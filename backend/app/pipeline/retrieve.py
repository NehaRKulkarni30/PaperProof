import asyncio
import html as html_lib
import io
import ipaddress
import json
import logging
import re
import socket
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pypdf import PdfReader
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import PaperCache
from app.sample_data import SAMPLE_FALLBACK_PAPERS

logger = logging.getLogger("paperproof.retrieve")
settings = get_settings()

API_SEMAPHORE = asyncio.Semaphore(4)
HEADERS = {
    "User-Agent": f"PaperProof/1.0 (mailto:{settings.contact_email})",
    "Accept": "application/json",
}

SECTION_HEADING_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*\.?\s+)?(Abstract|Introduction|Background|Related Work|Methods?|Methodology|"
    r"Model Architecture|Architecture|Experiments?|Experimental Setup|Results?|Evaluation|Discussion|"
    r"Analysis|Limitations|Conclusion|Conclusions|Future Work|Appendix)\b",
    re.IGNORECASE,
)


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def compute_match_score(parsed: Dict[str, Any], candidate: Dict[str, Any]) -> float:
    q_title = normalize_title(parsed.get("title", ""))
    c_title = normalize_title(candidate.get("title", ""))
    if not q_title or not c_title:
        # If matched directly via DOI or arXiv ID, trust high match
        if parsed.get("arxiv_id") or parsed.get("doi"):
            return 95.0
        return 0.0

    r1 = fuzz.ratio(q_title, c_title)
    r2 = fuzz.token_set_ratio(q_title, c_title)
    score = 0.55 * r1 + 0.45 * r2

    # Year penalty if wildly off
    q_year = parsed.get("year")
    c_year = candidate.get("year")
    if q_year and c_year:
        diff = abs(int(q_year) - int(c_year))
        if diff == 0:
            score = min(100.0, score + 4.0)
        elif diff == 1:
            score = min(100.0, score + 1.0)
        elif diff >= 4:
            score -= 18.0

    return round(max(0.0, min(100.0, score)), 1)


def chunk_pdf_pages(pdf_bytes: bytes, max_pages: int = 20) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception:
        return chunks

    current_section = "Body"
    for p_idx, page in enumerate(reader.pages[:max_pages], start=1):
        try:
            raw = page.extract_text() or ""
        except Exception:
            continue
        raw = re.sub(r"(\w)-\n(\w)", r"\1\2", raw)
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        buf: List[str] = []
        buf_len = 0

        for line in lines:
            if len(line) < 75 and SECTION_HEADING_RE.match(line):
                if buf and buf_len >= 60:
                    chunks.append({"section": current_section, "page": p_idx, "text": " ".join(buf)})
                    buf, buf_len = [], 0
                current_section = line[:60]
                continue
            # Stop before References section of the cited paper so we don't match its bibliography
            if re.match(r"^(?:\d+\.?\s+)?references$", line, re.IGNORECASE):
                if buf and buf_len >= 60:
                    chunks.append({"section": current_section, "page": p_idx, "text": " ".join(buf)})
                return chunks

            buf.append(line)
            buf_len += len(line) + 1
            if buf_len >= 900:
                chunks.append({"section": current_section, "page": p_idx, "text": " ".join(buf)})
                # Keep small overlap (last 2 lines)
                buf = buf[-2:]
                buf_len = sum(len(x) + 1 for x in buf)

        if buf and buf_len >= 50:
            chunks.append({"section": current_section, "page": p_idx, "text": " ".join(buf)})

    return chunks


def reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_map = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            pos_map[pos] = word
    if not pos_map:
        return ""
    return " ".join(pos_map[i] for i in sorted(pos_map.keys()))


async def _get_with_retry(client: httpx.AsyncClient, url: str, params: Optional[Dict] = None, timeout: float = 12.0):
    for attempt in range(3):
        try:
            resp = await client.get(url, params=params, headers=HEADERS, timeout=timeout, follow_redirects=True)
            if resp.status_code == 429:
                await asyncio.sleep(1.2 * (2 ** attempt))
                continue
            return resp
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt < 2:
                await asyncio.sleep(0.8 * (attempt + 1))
    return None


async def fetch_arxiv_by_id(client: httpx.AsyncClient, arxiv_id: str) -> Optional[Dict[str, Any]]:
    clean_id = re.sub(r"^arXiv:", "", arxiv_id, flags=re.IGNORECASE).strip()
    clean_id = re.sub(r"v\d+$", "", clean_id)
    url = f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(clean_id)}"
    resp = await _get_with_retry(client, url, timeout=12.0)
    if not resp or resp.status_code != 200:
        return None
    try:
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None
        title = re.sub(r"\s+", " ", (entry.findtext("atom:title", "", ns) or "")).strip()
        summary = re.sub(r"\s+", " ", (entry.findtext("atom:summary", "", ns) or "")).strip()
        if not title or "error" in title.lower():
            return None
        authors = [
            (a.findtext("atom:name", "", ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        ]
        published = entry.findtext("atom:published", "", ns) or ""
        year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
        return {
            "title": title,
            "authors": [a for a in authors if a],
            "year": year,
            "venue": "arXiv",
            "doi": f"10.48550/arXiv.{clean_id}",
            "arxiv_id": clean_id,
            "abstract": summary,
            "landing_url": f"https://arxiv.org/abs/{clean_id}",
            "pdf_url": f"https://arxiv.org/pdf/{clean_id}.pdf",
            "source_via": "arXiv id",
            "citation_count": None,
            "is_retracted": False,
        }
    except Exception as exc:
        logger.debug("arXiv parse failed for %s: %s", arxiv_id, exc)
        return None


async def search_arxiv(client: httpx.AsyncClient, title: str) -> Optional[Dict[str, Any]]:
    if not title or len(title) < 6:
        return None
    q = f'ti:"{title[:120]}"'
    url = f"https://export.arxiv.org/api/query?search_query={urllib.parse.quote(q)}&max_results=3"
    resp = await _get_with_retry(client, url, timeout=12.0)
    if not resp or resp.status_code != 200:
        return None
    try:
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        best = None
        best_r = 0.0
        for entry in root.findall("atom:entry", ns):
            cand_title = re.sub(r"\s+", " ", (entry.findtext("atom:title", "", ns) or "")).strip()
            if not cand_title:
                continue
            ratio = fuzz.token_set_ratio(normalize_title(title), normalize_title(cand_title))
            if ratio > best_r:
                best_r = ratio
                entry_id = entry.findtext("atom:id", "", ns) or ""
                m = re.search(r"/abs/([^\s]+)$", entry_id)
                ax_id = re.sub(r"v\d+$", "", m.group(1)) if m else None
                authors = [(a.findtext("atom:name", "", ns) or "").strip() for a in entry.findall("atom:author", ns)]
                published = entry.findtext("atom:published", "", ns) or ""
                year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
                best = {
                    "title": cand_title,
                    "authors": [a for a in authors if a],
                    "year": year,
                    "venue": "arXiv",
                    "doi": f"10.48550/arXiv.{ax_id}" if ax_id else None,
                    "arxiv_id": ax_id,
                    "abstract": re.sub(r"\s+", " ", (entry.findtext("atom:summary", "", ns) or "")).strip(),
                    "landing_url": f"https://arxiv.org/abs/{ax_id}" if ax_id else entry_id,
                    "pdf_url": f"https://arxiv.org/pdf/{ax_id}.pdf" if ax_id else None,
                    "source_via": "arXiv title search",
                    "citation_count": None,
                    "is_retracted": False,
                }
        return best
    except Exception:
        return None


async def fetch_crossref_by_doi(client: httpx.AsyncClient, doi: str) -> Optional[Dict[str, Any]]:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    resp = await _get_with_retry(client, url, timeout=10.0)
    if not resp or resp.status_code != 200:
        return None
    try:
        msg = resp.json().get("message", {})
        titles = msg.get("title") or []
        title = titles[0] if titles else ""
        authors = []
        for a in msg.get("author") or []:
            full = f"{a.get('given', '')} {a.get('family', '')}".strip()
            if full:
                authors.append(full)
        year = None
        for date_key in ("published-print", "published-online", "issued", "created"):
            parts = (msg.get(date_key) or {}).get("date-parts", [[]])
            if parts and parts[0]:
                year = parts[0][0]
                break
        abstract_raw = msg.get("abstract") or ""
        abstract = re.sub(r"<[^>]+>", " ", abstract_raw)
        abstract = re.sub(r"\s+", " ", abstract).strip()
        venue = (msg.get("container-title") or [""])[0]
        # Retraction check via CrossRef update-to / relation
        is_retracted = False
        for upd in msg.get("update-to") or []:
            if "retract" in str(upd.get("type", "")).lower() or "retract" in str(upd.get("label", "")).lower():
                is_retracted = True
        if "retracted" in title.lower():
            is_retracted = True
        pdf_url = None
        for link in msg.get("link") or []:
            if link.get("content-type") == "application/pdf" and link.get("URL"):
                pdf_url = link["URL"]
                break
        return {
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "doi": msg.get("DOI") or doi,
            "arxiv_id": None,
            "abstract": abstract,
            "landing_url": msg.get("URL") or f"https://doi.org/{doi}",
            "pdf_url": pdf_url,
            "source_via": "DOI (CrossRef)",
            "citation_count": msg.get("is-referenced-by-count"),
            "is_retracted": is_retracted,
        }
    except Exception:
        return None


async def search_crossref(client: httpx.AsyncClient, title: str, first_author: str = "", year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if not title:
        return None
    query = f"{title} {first_author}".strip()
    resp = await _get_with_retry(
        client,
        "https://api.crossref.org/works",
        params={"query.bibliographic": query[:200], "rows": 3},
        timeout=10.0,
    )
    if not resp or resp.status_code != 200:
        return None
    try:
        items = resp.json().get("message", {}).get("items", [])
        best = None
        best_r = 0.0
        for msg in items:
            titles = msg.get("title") or []
            cand_title = titles[0] if titles else ""
            if not cand_title:
                continue
            r = fuzz.token_set_ratio(normalize_title(title), normalize_title(cand_title))
            if r > best_r:
                best_r = r
                authors = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in (msg.get("author") or [])
                ]
                cand_year = None
                for dk in ("published-print", "published-online", "issued"):
                    parts = (msg.get(dk) or {}).get("date-parts", [[]])
                    if parts and parts[0]:
                        cand_year = parts[0][0]
                        break
                abstract = re.sub(r"<[^>]+>", " ", msg.get("abstract") or "")
                abstract = re.sub(r"\s+", " ", abstract).strip()
                is_retracted = any(
                    "retract" in str(u.get("type", "")).lower() or "retract" in str(u.get("label", "")).lower()
                    for u in (msg.get("update-to") or [])
                )
                doi = msg.get("DOI")
                best = {
                    "title": cand_title,
                    "authors": [a for a in authors if a],
                    "year": cand_year,
                    "venue": (msg.get("container-title") or [""])[0],
                    "doi": doi,
                    "arxiv_id": None,
                    "abstract": abstract,
                    "landing_url": msg.get("URL") or (f"https://doi.org/{doi}" if doi else None),
                    "pdf_url": None,
                    "source_via": "CrossRef title search",
                    "citation_count": msg.get("is-referenced-by-count"),
                    "is_retracted": is_retracted,
                }
        return best
    except Exception:
        return None


async def fetch_openalex_by_doi_or_search(
    client: httpx.AsyncClient,
    doi: Optional[str] = None,
    title: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        if doi:
            url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}"
            resp = await _get_with_retry(client, url, timeout=10.0)
            if not resp or resp.status_code != 200:
                return None
            work = resp.json()
            source_via = "DOI (OpenAlex)"
        elif title:
            resp = await _get_with_retry(
                client,
                "https://api.openalex.org/works",
                params={"search": title[:180], "per-page": 3},
                timeout=10.0,
            )
            if not resp or resp.status_code != 200:
                return None
            results = resp.json().get("results", [])
            if not results:
                return None
            work = max(
                results,
                key=lambda w: fuzz.token_set_ratio(normalize_title(title), normalize_title(w.get("title") or "")),
            )
            source_via = "OpenAlex title search"
        else:
            return None

        cand_title = work.get("title") or ""
        if not cand_title:
            return None
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in (work.get("authorships") or [])
        ]
        abstract = reconstruct_openalex_abstract(work.get("abstract_inverted_index"))
        oa = work.get("open_access") or {}
        best_loc = work.get("best_oa_location") or {}
        pdf_url = best_loc.get("pdf_url") or oa.get("oa_url")
        if pdf_url and not pdf_url.lower().endswith(".pdf") and "arxiv.org/pdf" not in pdf_url.lower():
            # Keep only likely PDF links for pdf_url
            pdf_url = best_loc.get("pdf_url")
        landing = best_loc.get("landing_page_url") or work.get("doi") or work.get("id")
        clean_doi = (work.get("doi") or "").replace("https://doi.org/", "") or doi
        venue = ((work.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        return {
            "title": cand_title,
            "authors": [a for a in authors if a],
            "year": work.get("publication_year"),
            "venue": venue,
            "doi": clean_doi,
            "arxiv_id": None,
            "abstract": abstract,
            "landing_url": landing,
            "pdf_url": pdf_url,
            "source_via": source_via,
            "citation_count": work.get("cited_by_count"),
            "is_retracted": bool(work.get("is_retracted", False)),
        }
    except Exception:
        return None


async def search_semantic_scholar(
    client: httpx.AsyncClient,
    doi: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    title: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    fields = "title,authors,year,venue,abstract,citationCount,openAccessPdf,url,externalIds"
    try:
        if arxiv_id:
            url = f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{urllib.parse.quote(arxiv_id)}"
            resp = await _get_with_retry(client, url, params={"fields": fields}, timeout=10.0)
            source_via = "arXiv id (Semantic Scholar)"
            if not resp or resp.status_code != 200:
                return None
            paper = resp.json()
        elif doi:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}"
            resp = await _get_with_retry(client, url, params={"fields": fields}, timeout=10.0)
            source_via = "DOI (Semantic Scholar)"
            if not resp or resp.status_code != 200:
                return None
            paper = resp.json()
        elif title:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            resp = await _get_with_retry(
                client,
                url,
                params={"query": title[:180], "limit": 3, "fields": fields},
                timeout=10.0,
            )
            source_via = "Semantic Scholar title search"
            if not resp or resp.status_code != 200:
                return None
            data = resp.json().get("data", [])
            if not data:
                return None
            paper = max(
                data,
                key=lambda p: fuzz.token_set_ratio(normalize_title(title), normalize_title(p.get("title") or "")),
            )
        else:
            return None

        if not paper or not paper.get("title"):
            return None
        ext = paper.get("externalIds") or {}
        ax = ext.get("ArXiv") or arxiv_id
        oa_pdf = (paper.get("openAccessPdf") or {}).get("url")
        if not oa_pdf and ax:
            oa_pdf = f"https://arxiv.org/pdf/{ax}.pdf"
        return {
            "title": paper.get("title"),
            "authors": [a.get("name", "") for a in (paper.get("authors") or []) if a.get("name")],
            "year": paper.get("year"),
            "venue": paper.get("venue") or "",
            "doi": ext.get("DOI") or doi,
            "arxiv_id": ax,
            "abstract": (paper.get("abstract") or "").strip(),
            "landing_url": paper.get("url") or (f"https://arxiv.org/abs/{ax}" if ax else None),
            "pdf_url": oa_pdf,
            "source_via": source_via,
            "citation_count": paper.get("citationCount"),
            "is_retracted": False,
        }
    except Exception:
        return None


def _is_safe_public_url(url: str) -> bool:
    """Validates that a reference URL is a public http(s) endpoint (prevents SSRF)."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").strip().lower()
        if not host or host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or host.endswith(".local"):
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            # Domain name: verify resolved IP is not private/loopback
            try:
                infos = socket.getaddrinfo(host, None)
                for info in infos[:3]:
                    ip = ipaddress.ip_address(info[4][0])
                    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                        return False
            except Exception:
                return False
        return True
    except Exception:
        return False


def _html_to_chunks(html_text: str, page_title: str = "") -> List[Dict[str, Any]]:
    """Extracts clean prose passages from an HTML webpage."""
    cleaned = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|aside)\b[^>]*>.*?</\1>", " ", html_text)
    cleaned = re.sub(r"(?i)</(p|div|li|h1|h2|h3|h4|tr|section|article|br)>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html_lib.unescape(cleaned)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in cleaned.split("\n")]
    lines = [ln for ln in lines if len(ln) >= 35]
    if not lines:
        return []

    chunks: List[Dict[str, Any]] = []
    buf: List[str] = []
    buf_len = 0
    for ln in lines[:120]:
        buf.append(ln)
        buf_len += len(ln) + 1
        if buf_len >= 850:
            chunks.append({"section": page_title[:60] or "Web Source", "page": 1, "text": " ".join(buf)})
            buf, buf_len = [], 0
            if len(chunks) >= 10:
                break
    if buf and buf_len >= 60 and len(chunks) < 10:
        chunks.append({"section": page_title[:60] or "Web Source", "page": 1, "text": " ".join(buf)})
    return chunks


async def fetch_public_reference_url(
    client: httpx.AsyncClient,
    url: str,
    parsed: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Fallback retriever for web documentation, gov reports, datasheets, and standards cited by URL."""
    if not url or not await asyncio.to_thread(_is_safe_public_url, url):
        return None
    try:
        web_headers = {
            "User-Agent": f"Mozilla/5.0 (compatible; PaperProof/1.0; mailto:{settings.contact_email})",
            "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
        }
        resp = await client.get(url, headers=web_headers, timeout=10.0, follow_redirects=True)
        if resp.status_code != 200 or not resp.content:
            return None
        if len(resp.content) > 6 * 1024 * 1024:
            return None

        ctype = (resp.headers.get("content-type") or "").lower()
        chunks: List[Dict[str, Any]] = []
        page_title = (parsed.get("title") or "").strip()

        if "pdf" in ctype or resp.content[:5].startswith(b"%PDF"):
            chunks = await asyncio.to_thread(chunk_pdf_pages, resp.content, 12)
        elif "html" in ctype or "text" in ctype:
            raw_html = resp.text[:400_000]
            t_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw_html)
            if t_m:
                extracted_title = re.sub(r"\s+", " ", html_lib.unescape(t_m.group(1))).strip()
                if extracted_title and len(extracted_title) >= 4:
                    page_title = extracted_title[:180]
            chunks = _html_to_chunks(raw_html, page_title)

        if not chunks:
            return None

        return {
            "title": page_title or parsed.get("title") or url,
            "authors": parsed.get("authors") or [],
            "year": parsed.get("year"),
            "venue": parsed.get("venue") or urllib.parse.urlparse(url).netloc,
            "doi": parsed.get("doi"),
            "arxiv_id": None,
            "abstract": chunks[0]["text"][:800],
            "chunks": chunks,
            "landing_url": str(resp.url),
            "pdf_url": str(resp.url) if ("pdf" in ctype or resp.content[:5].startswith(b"%PDF")) else None,
            "source_via": "Reference URL",
            "citation_count": None,
            "is_retracted": False,
            "evidence_level": "full_text" if len(chunks) >= 3 else "web_page",
        }
    except Exception as exc:
        logger.debug("Reference URL fetch failed (%s): %s", url, exc)
        return None


SCHOLARLY_URL_HOSTS = (
    "doi.org", "arxiv.org", "ieeexplore.ieee.org", "springer.com",
    "sciencedirect.com", "dl.acm.org", "nature.com", "semanticscholar.org",
)


def _is_non_scholarly_url(url: Optional[str]) -> bool:
    if not url:
        return False
    host_low = (urllib.parse.urlparse(url).hostname or "").lower()
    return bool(host_low) and not any(sh in host_low for sh in SCHOLARLY_URL_HOSTS)


def _cache_key(parsed: Dict[str, Any]) -> str:
    if parsed.get("arxiv_id"):
        return f"arxiv:{parsed['arxiv_id'].lower()}"
    if parsed.get("doi"):
        return f"doi:{parsed['doi'].lower()}"
    if _is_non_scholarly_url(parsed.get("url")):
        return f"url:{parsed['url'][:180].lower()}"
    title_norm = normalize_title(parsed.get("title", ""))[:180]
    year = parsed.get("year") or ""
    if title_norm:
        return f"title:{title_norm}:{year}"
    if parsed.get("url"):
        return f"url:{parsed['url'][:180].lower()}"
    return f"title:unknown:{year}"


def _read_cache_short(key: str) -> Optional[Dict[str, Any]]:
    sess = SessionLocal()
    try:
        cached = sess.query(PaperCache).filter(PaperCache.key == key).first()
        if cached:
            return json.loads(cached.json)
    except Exception:
        return None
    finally:
        sess.close()
    return None


def _write_cache_short(key: str, candidate: Dict[str, Any]):
    sess = SessionLocal()
    try:
        existing = sess.query(PaperCache).filter(PaperCache.key == key).first()
        serialized = json.dumps(candidate, ensure_ascii=False)
        if existing:
            existing.json = serialized
            existing.fetched_at = datetime.now(timezone.utc)
        else:
            sess.add(PaperCache(key=key, json=serialized, fetched_at=datetime.now(timezone.utc)))
        sess.commit()
    except Exception:
        sess.rollback()
    finally:
        sess.close()


async def download_and_chunk_pdf(client: httpx.AsyncClient, pdf_url: str) -> List[Dict[str, Any]]:
    if not pdf_url:
        return []
    try:
        resp = await client.get(pdf_url, headers=HEADERS, timeout=18.0, follow_redirects=True)
        if resp.status_code != 200:
            return []
        content_type = (resp.headers.get("content-type") or "").lower()
        if "pdf" not in content_type and not resp.content[:5].startswith(b"%PDF"):
            return []
        if len(resp.content) > 12 * 1024 * 1024:
            return []
        return await asyncio.to_thread(chunk_pdf_pages, resp.content, 18)
    except Exception as exc:
        logger.debug("PDF download failed (%s): %s", pdf_url, exc)
        return []


async def retrieve_paper(parsed: Dict[str, Any], db: Optional[Session] = None) -> Tuple[Dict[str, Any], bool, float]:
    """
    Retrieves original paper metadata, retraction flag, abstract, and open-access PDF chunks
    (plus safe public web URL fallback for documentation/gov reports).
    Uses short-lived DB sessions for cache reads/writes to prevent SQLAlchemy QueuePool exhaustion.
    Returns (resolved_dict, found: bool, match_score: float).
    """
    key = _cache_key(parsed)

    # Check SQLite cache via short-lived session (never hold a DB connection across HTTP calls)
    cached_data = _read_cache_short(key)
    if cached_data and cached_data.get("title"):
        score = compute_match_score(parsed, cached_data)
        is_url_src = cached_data.get("source_via") == "Reference URL"
        has_id = bool(parsed.get("arxiv_id") or parsed.get("doi") or is_url_src)
        # If cached entry has chunks/abstract (or wasn't just an empty metadata stub), use it
        if cached_data.get("chunks") or cached_data.get("abstract") or not parsed.get("url"):
            return cached_data, (score >= 65.0 or has_id), max(score, 85.0 if has_id else score)

    arxiv_id = parsed.get("arxiv_id")
    doi = parsed.get("doi")
    ref_url = (parsed.get("url") or "").strip()
    title = (parsed.get("title") or "").strip()
    authors = parsed.get("authors") or []
    first_author = authors[0].split(",")[0].split()[-1] if authors else ""
    year = parsed.get("year")

    candidate: Optional[Dict[str, Any]] = None

    async with API_SEMAPHORE:
        async with httpx.AsyncClient() as client:
            # Step A: Direct identifier lookup (arXiv ID or DOI)
            if arxiv_id:
                candidate = await fetch_arxiv_by_id(client, arxiv_id)
                if not candidate:
                    candidate = await search_semantic_scholar(client, arxiv_id=arxiv_id)
                # Enrich retraction & citation count via OpenAlex if DOI known
                if candidate and candidate.get("doi"):
                    oa_extra = await fetch_openalex_by_doi_or_search(client, doi=candidate["doi"])
                    if oa_extra:
                        candidate["citation_count"] = oa_extra.get("citation_count") or candidate.get("citation_count")
                        candidate["is_retracted"] = candidate.get("is_retracted") or oa_extra.get("is_retracted", False)

            if not candidate and doi:
                cr = await fetch_crossref_by_doi(client, doi)
                oa = await fetch_openalex_by_doi_or_search(client, doi=doi)
                if cr and oa:
                    candidate = {
                        **cr,
                        "abstract": cr.get("abstract") or oa.get("abstract") or "",
                        "pdf_url": cr.get("pdf_url") or oa.get("pdf_url"),
                        "citation_count": oa.get("citation_count") or cr.get("citation_count"),
                        "is_retracted": bool(cr.get("is_retracted") or oa.get("is_retracted")),
                    }
                else:
                    candidate = cr or oa
                if not candidate or not candidate.get("abstract"):
                    s2 = await search_semantic_scholar(client, doi=doi)
                    if s2:
                        if candidate:
                            candidate["abstract"] = candidate.get("abstract") or s2.get("abstract") or ""
                            candidate["pdf_url"] = candidate.get("pdf_url") or s2.get("pdf_url")
                            candidate["arxiv_id"] = candidate.get("arxiv_id") or s2.get("arxiv_id")
                        else:
                            candidate = s2

            # Step A2: If reference explicitly cites a non-scholarly web URL (gov/docs/datasheet) with no DOI/arXiv,
            # fetch that exact URL first so fuzzy title search doesn't accidentally grab an unrelated journal paper!
            if not candidate and not doi and not arxiv_id and _is_non_scholarly_url(ref_url):
                web_first = await fetch_public_reference_url(client, ref_url, parsed)
                if web_first:
                    candidate = web_first

            # Step B: Title + author + year search cascade: Semantic Scholar -> OpenAlex -> CrossRef -> arXiv
            # Do NOT break early on a match that lacks an abstract/PDF — keep enriching from remaining sources!
            if not candidate and title:
                best_cand: Optional[Dict[str, Any]] = None
                best_sc = 0.0
                for fn in (
                    lambda: search_semantic_scholar(client, title=title),
                    lambda: fetch_openalex_by_doi_or_search(client, title=title),
                    lambda: search_crossref(client, title=title, first_author=first_author, year=year),
                    lambda: search_arxiv(client, title=title),
                ):
                    res = await fn()
                    if not res:
                        continue
                    sc = compute_match_score(parsed, res)
                    if best_cand is None or sc > best_sc + 4.0:
                        if best_cand and sc >= 72.0:
                            # Merge useful fields from previous match
                            res["abstract"] = res.get("abstract") or best_cand.get("abstract") or ""
                            res["pdf_url"] = res.get("pdf_url") or best_cand.get("pdf_url")
                            res["doi"] = res.get("doi") or best_cand.get("doi")
                            res["is_retracted"] = bool(res.get("is_retracted") or best_cand.get("is_retracted"))
                        best_cand = res
                        best_sc = sc
                    elif sc >= 72.0 and best_cand is not None:
                        # Enrich existing strong match with missing abstract / PDF / DOI / citation count
                        if not best_cand.get("abstract") and res.get("abstract"):
                            best_cand["abstract"] = res["abstract"]
                        if not best_cand.get("pdf_url") and res.get("pdf_url"):
                            best_cand["pdf_url"] = res["pdf_url"]
                        if not best_cand.get("doi") and res.get("doi"):
                            best_cand["doi"] = res["doi"]
                        best_cand["citation_count"] = best_cand.get("citation_count") or res.get("citation_count")
                        best_cand["is_retracted"] = bool(best_cand.get("is_retracted") or res.get("is_retracted"))

                    # Stop early only when we have BOTH a strong title match AND actual text/PDF
                    if best_cand and best_sc >= 76.0 and (best_cand.get("abstract") or best_cand.get("pdf_url")):
                        break

                candidate = best_cand

                # If title search found a DOI (e.g. via CrossRef) but still no abstract, try DOI enrichment on OpenAlex/S2
                if candidate and candidate.get("doi") and not candidate.get("abstract") and not candidate.get("pdf_url"):
                    oa_en = await fetch_openalex_by_doi_or_search(client, doi=candidate["doi"])
                    if oa_en:
                        candidate["abstract"] = oa_en.get("abstract") or ""
                        candidate["pdf_url"] = candidate.get("pdf_url") or oa_en.get("pdf_url")
                    if not candidate.get("abstract"):
                        s2_en = await search_semantic_scholar(client, doi=candidate["doi"])
                        if s2_en:
                            candidate["abstract"] = s2_en.get("abstract") or ""
                            candidate["pdf_url"] = candidate.get("pdf_url") or s2_en.get("pdf_url")

            # Step C: Public URL fallback (official docs, gov sites, datasheets, IEA/DOE/NREL/Blynk/Arduino)
            if (not candidate or (not candidate.get("abstract") and not candidate.get("pdf_url"))) and ref_url:
                web_res = await fetch_public_reference_url(client, ref_url, parsed)
                if web_res:
                    if candidate and compute_match_score(parsed, candidate) >= 68.0:
                        candidate["chunks"] = web_res.get("chunks") or []
                        candidate["abstract"] = candidate.get("abstract") or web_res.get("abstract") or ""
                        candidate["landing_url"] = candidate.get("landing_url") or web_res.get("landing_url")
                    else:
                        candidate = web_res

            # Safety net for the two sample papers if external APIs are offline
            if not candidate and arxiv_id and arxiv_id in SAMPLE_FALLBACK_PAPERS:
                candidate = dict(SAMPLE_FALLBACK_PAPERS[arxiv_id])
            elif not candidate and title:
                for fb_id, fb in SAMPLE_FALLBACK_PAPERS.items():
                    if fuzz.token_set_ratio(normalize_title(title), normalize_title(fb["title"])) >= 85:
                        candidate = dict(fb)
                        break

            if not candidate:
                return {"error": "not found / possible fabricated or wrong reference"}, False, 0.0

            is_web_source = candidate.get("source_via") == "Reference URL"
            score = compute_match_score(parsed, candidate)
            direct_id_match = bool(arxiv_id or doi or is_web_source)
            if not direct_id_match and score < 68.0:
                # Last chance: if reference has a URL, try fetching it directly
                if ref_url:
                    web_res = await fetch_public_reference_url(client, ref_url, parsed)
                    if web_res:
                        candidate = web_res
                        is_web_source = True
                        direct_id_match = True
                        score = max(score, 85.0)
                if not direct_id_match and score < 68.0:
                    return {
                        "closest_candidate": candidate.get("title"),
                        "error": "not found / possible fabricated or wrong reference",
                        "match_score": score,
                    }, False, score

            if direct_id_match and score < 65.0:
                score = max(score, 88.0)

            # Download and chunk open-access PDF if not already populated
            chunks = candidate.get("chunks") or []
            if not chunks and candidate.get("pdf_url"):
                chunks = await download_and_chunk_pdf(client, candidate["pdf_url"])

            # Always ensure abstract is indexed as a first-class chunk
            abstract = (candidate.get("abstract") or "").strip()
            if abstract:
                has_abs = any(c.get("section", "").lower() == "abstract" for c in chunks)
                if not has_abs:
                    chunks.insert(0, {"section": "Abstract", "page": 1, "text": abstract})

            # If PDF download failed for sample papers, augment with cached sample chunks
            if len(chunks) <= 1 and candidate.get("arxiv_id") in SAMPLE_FALLBACK_PAPERS:
                chunks = list(SAMPLE_FALLBACK_PAPERS[candidate["arxiv_id"]]["chunks"])

            candidate["chunks"] = chunks
            if len(chunks) >= 3:
                candidate["evidence_level"] = "full_text"
            elif chunks:
                candidate["evidence_level"] = "web_page" if is_web_source else "abstract_only"
            else:
                candidate["evidence_level"] = "metadata_only"

    # Store in SQLite PaperCache via short-lived session
    if candidate.get("title"):
        _write_cache_short(key, candidate)

    return candidate, True, score
