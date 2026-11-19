import re
from typing import Any, Dict, List, Tuple

from app.pipeline.llm import gemini_client

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b", re.IGNORECASE)
ARXIV_RE = re.compile(
    r"(?:arXiv\s*[:\s]\s*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})",
    re.IGNORECASE,
)
URL_RE = re.compile(r"(https?://[^\s,)\]>]+)", re.IGNORECASE)
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})[a-z]?\b")


def extract_identifiers(text: str) -> Dict[str, Any]:
    doi_m = DOI_RE.search(text or "")
    arxiv_m = ARXIV_RE.search(text or "")
    url_m = URL_RE.search(text or "")

    doi = doi_m.group(1).rstrip(".,;)") if doi_m else None
    arxiv_id = arxiv_m.group(1).rstrip(".,;)").replace(".pdf", "") if arxiv_m else None
    if arxiv_id and "v" in arxiv_id:
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
    url = url_m.group(1).rstrip(".,;)") if url_m else None
    return {"doi": doi, "arxiv_id": arxiv_id, "url": url}


def split_reference_entries(references_text: str) -> List[Tuple[str, str]]:
    """
    Splits a references block into (marker, raw_text) tuples.
    Supports:
      - Bracketed numeric: [1] ..., [2] ...
      - Dotted numeric: 1. ..., 2. ...
      - Author-year entries separated by blank lines or author-year line starts.
    """
    if not references_text or not references_text.strip():
        return []

    text = references_text.strip()

    # Pattern 1: Bracketed numeric [1]
    bracket_matches = list(re.finditer(r"(?m)^\s*\[(\d+)\]\s+", text))
    if len(bracket_matches) >= 1:
        entries = []
        for i, m in enumerate(bracket_matches):
            start = m.start()
            end = bracket_matches[i + 1].start() if i + 1 < len(bracket_matches) else len(text)
            raw = re.sub(r"\s+", " ", text[start:end]).strip()
            entries.append((f"[{m.group(1)}]", raw))
        return entries

    # Pattern 2: Numbered list "1. Author..."
    num_matches = list(re.finditer(r"(?m)^\s*(\d+)\.\s+(?=[A-Z])", text))
    if len(num_matches) >= 2:
        entries = []
        for i, m in enumerate(num_matches):
            start = m.start()
            end = num_matches[i + 1].start() if i + 1 < len(num_matches) else len(text)
            raw = re.sub(r"\s+", " ", text[start:end]).strip()
            entries.append((f"[{m.group(1)}]", raw))
        return entries

    # Pattern 3: Paragraph-separated author-year entries
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) <= 2 and "\n" in text:
        # Try splitting on lines that start with "Surname, I." (handles single-spaced PDF bibliographies)
        ay_lines = [l.strip() for l in text.split("\n") if l.strip()]
        grouped = []
        for line in ay_lines:
            # Skip publisher download footers
            if re.match(r"^(?:Presses de |Downloaded |Téléchargé )", line, re.IGNORECASE):
                continue
            if re.match(r"^[A-ZÀ-ÿ][A-Za-zÀ-ÿ'\-]+,\s+[A-Z]", line) and grouped:
                grouped.append(line)
            elif grouped:
                grouped[-1] = grouped[-1] + " " + line
            else:
                grouped.append(line)
        if len(grouped) > len(paragraphs):
            paragraphs = grouped

    entries = []
    for idx, p in enumerate(paragraphs, start=1):
        if len(p) < 15:
            continue
        # Derive author-year marker like "(Vaswani, 2017)"
        surname_m = re.match(r"^([A-Z][A-Za-z'\-]+)", p)
        year_m = YEAR_RE.search(p)
        if surname_m and year_m:
            marker = f"({surname_m.group(1)}, {year_m.group(1)})"
        else:
            marker = f"[{idx}]"
        entries.append((marker, p))
    return entries


def heuristic_parse_reference(marker: str, raw_text: str) -> Dict[str, Any]:
    ids = extract_identifiers(raw_text)
    cleaned = re.sub(r"^\s*(?:\[\d+\]|\d+\.)\s*", "", raw_text).strip()
    year_m = YEAR_RE.search(cleaned)
    year = int(year_m.group(1)) if year_m else None

    authors: List[str] = []
    title = ""
    venue = ""

    # IEEE / quoted-title style: Authors, "Paper Title," Venue, pp. 1-5, 2015.
    quote_m = re.search(r'["“]([^"”]{8,240})["”]', cleaned)
    if quote_m:
        title = quote_m.group(1).strip(" .,;:")
        before_q = cleaned[: quote_m.start()].strip(" ,.;:()")
        after_q = cleaned[quote_m.end() :].strip(" ,.;:")
        # Strip trailing year like "(2015)" or "[2015]" from author part
        before_q = re.sub(r"[\(\[]\s*(?:19|20)\d{2}[a-z]?\s*[\)\]]\.?$", "", before_q).strip(" ,.;:")
        if before_q:
            authors = [a.strip(" ,&.") for a in re.split(r"(?:,\s*(?:&|and)\s*|\s+&\s+|\s+and\s+|;)", before_q) if a.strip()]
        venue = after_q
    elif year_m:
        # APA / Author (YYYY). Title. Venue.
        before_year = cleaned[: year_m.start()].strip(" ([,.")
        after_year = cleaned[year_m.end() :].strip(" )\].,:")
        if before_year:
            authors = [a.strip(" ,&") for a in re.split(r"(?:,\s*&|&|\band\b|;)", before_year) if a.strip()]
        if after_year:
            parts = re.split(r"\.\s+", after_year, maxsplit=1)
            title = parts[0].strip(" .")
            venue = parts[1].strip(" .") if len(parts) > 1 else ""
        else:
            # Year at end without quotes
            parts = re.split(r"\.\s+", before_year, maxsplit=2)
            if len(parts) >= 2:
                authors = [parts[0].strip()]
                title = parts[1].strip()
                venue = parts[2].strip() if len(parts) > 2 else ""
    else:
        parts = re.split(r"\.\s+", cleaned, maxsplit=2)
        if len(parts) >= 2:
            authors = [parts[0].strip()]
            title = parts[1].strip()
            venue = parts[2].strip() if len(parts) > 2 else ""
        else:
            title = cleaned[:180]

    # Clean trailing arXiv/DOI/URL from venue/title
    title = re.sub(r"\s*(?:arXiv:\S+|doi:\S+|https?://\S+|Available:\s*\S+).*$", "", title, flags=re.IGNORECASE).strip(" .,")
    venue = re.sub(r"\s*(?:arXiv:\S+|doi:\S+|https?://\S+|Available:\s*\S+).*$", "", venue, flags=re.IGNORECASE).strip(" .,")

    return {
        "marker": marker,
        "authors": authors[:10],
        "year": year,
        "title": title or cleaned[:140],
        "venue": venue,
        "doi": ids["doi"],
        "arxiv_id": ids["arxiv_id"],
        "url": ids["url"],
    }


async def parse_references(references_text: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Returns (list of parsed references, used_gemini: bool).
    Each item has keys: marker, raw_text, parsed: {marker, authors, year, title, venue, doi, arxiv_id, url}.
    """
    raw_entries = split_reference_entries(references_text)
    if not raw_entries:
        return [], False

    # Cap at 60 references for speed
    raw_entries = raw_entries[:60]

    heuristic_results = []
    for marker, raw in raw_entries:
        parsed = heuristic_parse_reference(marker, raw)
        heuristic_results.append({"marker": marker, "raw_text": raw, "parsed": parsed})

    # Ask Gemini to parse structured bibliographic fields cleanly in one batch call
    entries_block = "\n".join(f"{idx+1}. MARKER={m} | RAW={r}" for idx, (m, r) in enumerate(raw_entries))
    prompt = f"""Parse the following academic reference entries into a JSON object with a single key "references", which is a list of objects in the EXACT same order.

Each object must have:
- "marker": string (the citation marker, e.g. "[1]" or "(Vaswani, 2017)")
- "authors": list of strings (author names)
- "year": integer or null
- "title": string (paper title, without quotes)
- "venue": string (journal/conference/publisher, or "")
- "doi": string or null
- "arxiv_id": string or null (just the ID like "1706.03762", no "arXiv:" prefix)
- "url": string or null

References to parse:
{entries_block}
"""
    llm_resp = await gemini_client.generate_json(
        prompt,
        system_instruction="You are a precise academic bibliography parser. Return strict JSON only.",
    )

    if isinstance(llm_resp, dict) and isinstance(llm_resp.get("references"), list):
        llm_refs = llm_resp["references"]
        if len(llm_refs) == len(raw_entries):
            merged = []
            for (marker, raw), llm_item, heur in zip(raw_entries, llm_refs, heuristic_results):
                ids = extract_identifiers(raw)
                arxiv_val = llm_item.get("arxiv_id") or ids["arxiv_id"]
                if isinstance(arxiv_val, str):
                    arxiv_val = re.sub(r"^arXiv:", "", arxiv_val, flags=re.IGNORECASE).strip()
                    arxiv_val = re.sub(r"v\d+$", "", arxiv_val)
                parsed = {
                    "marker": marker,
                    "authors": llm_item.get("authors") if isinstance(llm_item.get("authors"), list) else heur["parsed"]["authors"],
                    "year": llm_item.get("year") if isinstance(llm_item.get("year"), int) else heur["parsed"]["year"],
                    "title": (llm_item.get("title") or heur["parsed"]["title"] or "").strip(),
                    "venue": (llm_item.get("venue") or heur["parsed"]["venue"] or "").strip(),
                    "doi": llm_item.get("doi") or ids["doi"],
                    "arxiv_id": arxiv_val or None,
                    "url": llm_item.get("url") or ids["url"],
                }
                merged.append({"marker": marker, "raw_text": raw, "parsed": parsed})
            return merged, True

    return heuristic_results, False
