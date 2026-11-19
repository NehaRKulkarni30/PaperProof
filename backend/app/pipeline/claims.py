import re
from typing import Any, Dict, List, Optional, Tuple
from rapidfuzz import fuzz

from app.pipeline.llm import gemini_client

# Matches [1], [1, 2], [1-3], or (Vaswani et al., 2017), (Devlin & Chang, 2019), or Brockett [1910]
NUMERIC_CITE_RE = re.compile(r"\[(\d+(?:\s*[,;\-–]\s*\d+)*)\]")
AUTHOR_YEAR_CITE_RE = re.compile(
    r"\(([A-Z][A-Za-z'\-]+(?:\s+(?:et\s+al\.|&|and)\s*[A-Za-z'\-\.]*)?,?\s*(?:19|20)\d{2}[a-z]?(?:;\s*[A-Z][A-Za-z'\-]+[^)]*(?:19|20)\d{2}[a-z]?)*)\)"
)
BRACKET_AUTHOR_YEAR_RE = re.compile(
    r"\b([A-Z][A-Za-z'\-]+(?:\s+(?:et\s+al\.|&|and)\s+[A-Z][A-Za-z'\-]+)?)\s*\[((?:18|19|20)\d{2}[a-z]?)\]"
)

STAT_OR_CLAIM_CUE_RE = re.compile(
    r"(\b\d+(?:\.\d+)?\s*%|\b(?:improve[ds]?|increas(?:e[ds]?|ing)|decreas(?:e[ds]?|ing)|reduc(?:e[ds]?|ing)|"
    r"outperform(?:s|ed)?|achiev(?:e[ds]?|ing)|demonstrat(?:e[ds]?|ing)|found|show(?:n|s|ed)|propos(?:e[ds]?)|"
    r"introduc(?:e[ds]?)|develop(?:ed|s)?|design(?:ed|s)?|reli(?:es|ed)|always|never|cheaper|faster|"
    r"significant(?:ly)?|state-of-the-art|benchmark|study|experiment|temperature|efficiency|energy\s+density|thermal)\b)",
    re.IGNORECASE,
)

# Boilerplate headings/lines common in student mini-project reports to skip when extracting claims
BOILERPLATE_RE = re.compile(
    r"\b(?:bonafide\s+student|partial\s+fulfilment|award\s+of\s+the\s+degree|express\s+our\s+sincere\s+gratitude|"
    r"heartfelt\s+thanks|internal\s+assessment|table\s+of\s+contents|list\s+of\s+figures|list\s+of\s+tables|"
    r"certified\s+that\s+the\s+mini\s+project|autonomous\s+institute|affiliated\s+to)\b",
    re.IGNORECASE,
)


def expand_numeric_markers(inner: str) -> List[str]:
    markers = []
    for part in re.split(r"[,;]", inner):
        part = part.strip()
        range_m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
        if range_m:
            a, b = int(range_m.group(1)), int(range_m.group(2))
            if a < 1000 and b < 1000 and b >= a and (b - a) <= 15:
                for n in range(a, b + 1):
                    markers.append(f"[{n}]")
        elif part.isdigit():
            val = int(part)
            # Ignore 4-digit years like [1910] or [2015] as numeric ref indices
            if 1 <= val < 1000:
                markers.append(f"[{val}]")
    return markers


def extract_markers_from_text(text: str) -> List[str]:
    markers: List[str] = []
    for m in NUMERIC_CITE_RE.finditer(text or ""):
        for mk in expand_numeric_markers(m.group(1)):
            if mk not in markers:
                markers.append(mk)
    for m in AUTHOR_YEAR_CITE_RE.finditer(text or ""):
        inner = m.group(1)
        for part in inner.split(";"):
            mk = f"({part.strip()})"
            if mk not in markers:
                markers.append(mk)
    for m in BRACKET_AUTHOR_YEAR_RE.finditer(text or ""):
        mk = f"({m.group(1).strip()}, {m.group(2).strip()})"
        if mk not in markers:
            markers.append(mk)
    return markers


def _extract_reference_surnames(ref: Dict[str, Any]) -> List[str]:
    """Extracts candidate author surnames (len >= 4) from a parsed reference."""
    parsed = ref.get("parsed", {})
    authors = parsed.get("authors") or []
    surnames: List[str] = []
    stop_org = {
        "department", "energy", "national", "laboratory", "international", "agency",
        "documentation", "datasheet", "platform", "series", "university", "press",
        "institute", "technologies", "office", "center", "centre", "available",
    }
    for auth in authors[:3]:
        a = (auth or "").strip()
        if not a:
            continue
        # Handle "Surname, Initials" vs "Initials Surname"
        if "," in a:
            cand = a.split(",")[0].strip()
        else:
            parts = [p.strip(".") for p in a.split() if len(p.strip(".")) >= 3]
            cand = parts[-1] if parts else ""
        cand_clean = re.sub(r"[^A-Za-z'\-]", "", cand)
        if len(cand_clean) >= 4 and cand_clean.lower() not in stop_org:
            if cand_clean not in surnames:
                surnames.append(cand_clean)
    return surnames


def find_narrative_reference_matches(text: str, parsed_refs: List[Dict[str, Any]]) -> List[int]:
    """
    Matches narrative/prose citations commonly written in student literature reviews, e.g.:
    'Folianto et al. proposed a SmartBin system...' -> Reference [2]
    'Anitha developed an IoT-based garbage monitoring system...' -> Reference [8]
    """
    if not text or not parsed_refs:
        return []
    low = text.lower()
    matched: List[int] = []
    narrative_verb = (
        r"(?:et\s+al\.?|proposed|developed|designed|presented|introduced|reported|"
        r"demonstrated|showed|studied|implemented|built|created|investigated|used|found)"
    )

    for idx, ref in enumerate(parsed_refs):
        # 1. Check author surname near narrative verb or 'et al.'
        for surname in _extract_reference_surnames(ref):
            s_esc = re.escape(surname.lower())
            if re.search(rf"\b{s_esc}\b(?:\s+[a-z'\-]+){{0,2}}\s+{narrative_verb}\b", low):
                matched.append(idx)
                break
        if idx in matched:
            continue

        # 2. Check distinctive title substring (>= 20 chars) mentioned in text
        title = (ref.get("parsed", {}).get("title") or "").strip()
        if len(title) >= 18:
            # Check colon-prefixed system name like "Smartbin" or distinctive phrase
            norm_title = re.sub(r"[^a-z0-9\s]", " ", title.lower())
            norm_title = re.sub(r"\s+", " ", norm_title).strip()
            if len(norm_title) >= 18 and norm_title in re.sub(r"[^a-z0-9\s]", " ", low):
                matched.append(idx)
    return matched


def map_marker_to_reference(marker: str, parsed_refs: List[Dict[str, Any]]) -> Optional[int]:
    """Returns index in parsed_refs or None if not found."""
    if not marker or not parsed_refs:
        return None
    norm = marker.strip()

    # Exact numeric match [1]
    num_m = re.match(r"^\[?(\d+)\]?$", norm)
    if num_m:
        target = f"[{num_m.group(1)}]"
        for idx, ref in enumerate(parsed_refs):
            if ref["marker"].strip() == target:
                return idx
        return None

    # Author-year match (Vaswani et al., 2017)
    year_m = re.search(r"((?:19|20)\d{2})", norm)
    year = int(year_m.group(1)) if year_m else None
    surname_m = re.search(r"([A-Z][A-Za-z'\-]+)", norm)
    surname = surname_m.group(1).lower() if surname_m else ""

    best_idx = None
    best_score = 0
    for idx, ref in enumerate(parsed_refs):
        parsed = ref.get("parsed", {})
        ref_year = parsed.get("year")
        authors_str = " ".join(parsed.get("authors", [])).lower() + " " + ref.get("raw_text", "").lower()[:100]
        score = 0
        if surname and surname in authors_str:
            score += 60
        if year and ref_year == year:
            score += 40
        elif year and ref_year and abs(ref_year - year) == 1:
            score += 15
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_score >= 60:
        return best_idx

    # Fuzzy fallback on marker string
    for idx, ref in enumerate(parsed_refs):
        if fuzz.ratio(norm.lower(), ref["marker"].lower()) >= 80:
            return idx
    return None


def heuristic_extract_claims(
    body_pages: List[Dict[str, Any]],
    parsed_refs: Optional[List[Dict[str, Any]]] = None,
    max_claims: int = 25,
) -> List[Dict[str, Any]]:
    candidates = []
    parsed_refs = parsed_refs or []
    for p in body_pages:
        page_num = p.get("page", 1)
        text = p.get("text", "")
        # Split into sentences carefully avoiding abbreviations like "et al." or "e.g."
        protected = re.sub(r"\b(et al|e\.g|i\.e|Fig|Eq|Dr|Prof|vs)\.", r"\1<DOT>", text)
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])|\n+", protected)
        for sent in sentences:
            s = sent.replace("<DOT>", ".").strip()
            if len(s) < 28 or len(s) > 650:
                continue
            if BOILERPLATE_RE.search(s):
                continue
            # Skip headings and table rows
            if "|" in s:
                continue
            if re.match(r"^(?:\d+(?:\.\d+)*\.?\s+)?[A-Z][A-Za-z\s\-:]{2,60}$", s) and "." not in s:
                continue
            markers = extract_markers_from_text(s)
            narr_matches = find_narrative_reference_matches(s, parsed_refs) if not markers else []
            has_stat = bool(STAT_OR_CLAIM_CUE_RE.search(s))
            if markers or narr_matches or has_stat:
                priority = (
                    (100 if markers else 0)
                    + (85 if narr_matches else 0)
                    + (25 if re.search(r"\d+%?", s) else 0)
                    + (15 if has_stat else 0)
                )
                candidates.append(
                    {
                        "text": s,
                        "page": page_num,
                        "markers": markers,
                        "narrative_indices": narr_matches,
                        "priority": priority,
                    }
                )

    # Sort cited / narrative-cited claims first while preserving reading order
    cited = [c for c in candidates if c["markers"] or c["narrative_indices"]]
    uncited = [c for c in candidates if not c["markers"] and not c["narrative_indices"]]
    selected = cited[:max_claims]
    remaining = max_claims - len(selected)
    if remaining > 0 and len(cited) < 5:
        cap = min(remaining, 8 if parsed_refs else 3)
        uncited_sorted = sorted(uncited, key=lambda x: -x["priority"])[:cap]
        selected.extend(uncited_sorted)

    ordered = [c for c in candidates if c in selected][:max_claims]
    return [
        {"text": c["text"], "page": c["page"], "markers": c["markers"]}
        for c in ordered
    ]


async def extract_claims_and_map(
    body_pages: List[Dict[str, Any]],
    parsed_refs: List[Dict[str, Any]],
    max_claims: int = 25,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Extracts up to max_claims important scientific/factual claims with verbatim text,
    page numbers, citation markers, and mapped reference indices.
    Handles formal research papers AND student mini-project / case study reports
    (narrative citations like 'Folianto et al. proposed...' and bibliography-at-end reports).
    """
    # Build page-annotated text (truncate safely to ~32k chars for prompt)
    annotated_chunks = []
    total_len = 0
    for p in body_pages:
        block = f"[PAGE {p['page']}]\n{p['text']}"
        if total_len + len(block) > 32000:
            annotated_chunks.append(block[: max(0, 32000 - total_len)])
            break
        annotated_chunks.append(block)
        total_len += len(block)
    doc_text = "\n\n".join(annotated_chunks)

    def _fmt_ref(r: Dict[str, Any]) -> str:
        p = r.get("parsed", {})
        auths = ", ".join((p.get("authors") or [])[:3])
        yr = p.get("year") or ""
        title = p.get("title") or ""
        return f"- {r['marker']}: {auths + ' — ' if auths else ''}{title} ({yr})"

    ref_summary = "\n".join(_fmt_ref(r) for r in parsed_refs) or "(No references section detected)"

    # Detect whether the body uses explicit inline markers or is a narrative/bibliography-at-end report
    inline_marker_count = sum(len(extract_markers_from_text(p.get("text", ""))) for p in body_pages)
    has_refs = len(parsed_refs) > 0
    student_report_guidance = ""
    if has_refs and inline_marker_count < 3:
        student_report_guidance = (
            "\n7. IMPORTANT (Student Project / Case Study Report Mode): This document has a References section "
            "but few or no inline bracket markers like [1] in the body text. Extract 5 to 12 key verifiable "
            "literature-review, background, or technical factual claims (skip certificates, acknowledgements, "
            "table of contents, hardware shopping lists, and 'in this project we built...' descriptions). "
            "Whenever a claim discusses an author or paper listed in the Parsed reference list (e.g. 'Folianto et al. proposed...' "
            "or 'Longhi et al. developed...'), put that reference's marker (e.g. \"[2]\") in \"markers\"!"
        )

    prompt = f"""Extract the important factual or scientific claims from the document body below (statements, findings, literature-review summaries, numbers, statistics, or conclusions that require evidence).

Rules:
1. ALWAYS extract EVERY claim that carries an explicit inline citation marker like [1], [2], [3] or (Author, Year) — EVEN IF that citation marker is missing from the Parsed reference list (so missing references can be caught and flagged). Also prioritize narrative author citations like "Smith et al. proposed..." matching the Parsed reference list, plus claims containing specific technical facts, numbers, or percentages.
2. Return AT MOST {max_claims} claims, in the order they appear in the document.
3. Each claim's "text" MUST be copied verbatim from the document (keep any citation marker inside the text if it appears there). If a sentence introduces a quoted/embedded claim with a citation, extract the specific claim sentence/clause cleanly.
4. Preserve the integer "page" from the [PAGE N] markers.
5. List all citation markers appearing in that claim in "markers" (e.g. ["[1]"] or ["(Vaswani et al., 2017)"]). If the claim narratively names an author/paper from the Parsed reference list (e.g. "Folianto et al. proposed a SmartBin system"), include that reference's marker (e.g. ["[2]"]) in "markers". Use [] if no reference is named or cited.
6. Do NOT extract bibliography entries themselves, cover page text, certificates, acknowledgements, table of contents, or generic filler sentences.{student_report_guidance}

Parsed reference list for context:
{ref_summary}

Return strict JSON with a single key "claims":
{{
  "claims": [
    {{
      "text": "verbatim claim from document",
      "page": 1,
      "markers": ["[1]"]
    }}
  ]
}}

Document body:
{doc_text}
"""
    llm_resp = await gemini_client.generate_json(
        prompt,
        system_instruction="You are an expert scientific peer-reviewer extracting verifiable claims and citations. Output strict JSON only.",
    )

    used_gemini = False
    raw_claims: List[Dict[str, Any]] = []

    if isinstance(llm_resp, dict) and isinstance(llm_resp.get("claims"), list) and len(llm_resp["claims"]) > 0:
        used_gemini = True
        for item in llm_resp["claims"][:max_claims]:
            if not isinstance(item, dict):
                continue
            txt = (item.get("text") or "").strip()
            if len(txt) < 12 or BOILERPLATE_RE.search(txt):
                continue
            markers = item.get("markers") if isinstance(item.get("markers"), list) else []
            # Also merge regex-detected markers so none are missed
            regex_markers = extract_markers_from_text(txt)
            merged_markers = []
            for mk in list(markers) + regex_markers:
                mk_str = str(mk).strip()
                # Filter out bare 4-digit years like "[1910]" mistakenly emitted as numeric markers
                if re.match(r"^\[(?:18|19|20)\d{2}\]$", mk_str):
                    continue
                if mk_str and mk_str not in merged_markers:
                    merged_markers.append(mk_str)
            page_val = item.get("page", 1)
            try:
                page_val = max(1, int(page_val))
            except Exception:
                page_val = 1
            raw_claims.append({"text": txt, "page": page_val, "markers": merged_markers})

    if not raw_claims:
        raw_claims = heuristic_extract_claims(body_pages, parsed_refs=parsed_refs, max_claims=max_claims)
        used_gemini = False
    elif has_refs and inline_marker_count < 3 and len(raw_claims) < 4:
        # Ensure bibliography-at-end student reports get a meaningful set of factual claims even if LLM is overly conservative
        existing_low = {c["text"].lower()[:80] for c in raw_claims}
        for hc in heuristic_extract_claims(body_pages, parsed_refs=parsed_refs, max_claims=10):
            if len(raw_claims) >= 8:
                break
            if hc["text"].lower()[:80] not in existing_low:
                raw_claims.append(hc)
                existing_low.add(hc["text"].lower()[:80])

    # Map each claim's markers (and narrative author mentions) to parsed_refs
    mapped_claims = []
    for idx, claim in enumerate(raw_claims, start=1):
        markers = list(claim["markers"])
        ref_indices: List[int] = []
        missing_markers: List[str] = []
        narrative_matched = False

        for mk in markers:
            found_idx = map_marker_to_reference(mk, parsed_refs)
            if found_idx is not None:
                if found_idx not in ref_indices:
                    ref_indices.append(found_idx)
            else:
                missing_markers.append(mk)

        # Fallback: narrative author/title match in the claim sentence (e.g., "Folianto et al. proposed...")
        if not ref_indices and parsed_refs:
            narr_hits = find_narrative_reference_matches(claim["text"], parsed_refs)
            if narr_hits:
                ref_indices.extend(narr_hits)
                narrative_matched = True
                for hi in narr_hits:
                    mk_val = parsed_refs[hi]["marker"]
                    if mk_val not in markers:
                        markers.append(mk_val)

        ref_idx = ref_indices[0] if ref_indices else None

        mapped_claims.append(
            {
                "idx": idx,
                "text": claim["text"],
                "page": claim["page"],
                "markers": markers,
                "reference_idx": ref_idx,
                "reference_indices": ref_indices,
                "missing_markers": missing_markers,
                "is_uncited": len(markers) == 0 and len(ref_indices) == 0,
                "narrative_matched": narrative_matched,
            }
        )

    return mapped_claims, used_gemini
