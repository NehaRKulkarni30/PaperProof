import math
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from rapidfuzz import fuzz

from app.pipeline.llm import gemini_client

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by", "from", "at",
    "as", "is", "are", "was", "were", "be", "been", "being", "that", "this", "these", "those",
    "it", "its", "we", "our", "they", "their", "which", "who", "whom", "has", "have", "had",
    "can", "could", "may", "might", "will", "would", "than", "into", "over", "such", "also",
    "using", "used", "based", "between", "through", "about", "more", "most", "both",
}

VALID_VERDICTS = {
    "supported",
    "partly_supported",
    "unsupported",
    "contradictory",
    "possibly_outdated",
    "reference_not_found",
}

TIME_SENSITIVE_RE = re.compile(
    r"\b(current(?:ly)?|today|state[- ]of[- ]the[- ]art|sota|latest|recent(?:ly)?|modern|nowadays|best[- ]performing|leading)\b",
    re.IGNORECASE,
)

NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%?|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|fifty|hundred)\b", re.IGNORECASE)


def _light_stem(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9%]+", (text or "").lower())
    return [_light_stem(t) for t in tokens if len(t) > 1 and t not in STOPWORDS]


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def select_top_passages(claim_text: str, chunks: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """BM25-inspired passage retrieval over the source paper chunks."""
    if not chunks:
        return []
    if len(chunks) <= top_k:
        return chunks

    q_tokens = tokenize(claim_text)
    if not q_tokens:
        return chunks[:top_k]

    doc_tokens = [tokenize(c.get("text", "")) for c in chunks]
    avgdl = sum(len(d) for d in doc_tokens) / max(len(doc_tokens), 1)
    df = Counter()
    for d in doc_tokens:
        for w in set(d):
            df[w] += 1

    N = len(chunks)
    k1, b = 1.5, 0.75
    scored = []
    for idx, (chunk, d_toks) in enumerate(zip(chunks, doc_tokens)):
        tf = Counter(d_toks)
        dl = len(d_toks) or 1
        score = 0.0
        for q in q_tokens:
            if tf[q] > 0:
                idf = math.log(1 + (N - df[q] + 0.5) / (df[q] + 0.5))
                score += idf * ((tf[q] * (k1 + 1)) / (tf[q] + k1 * (1 - b + b * dl / max(avgdl, 1))))
        # Slight boost for Abstract / Introduction / Conclusion
        sec_low = (chunk.get("section") or "").lower()
        if "abstract" in sec_low:
            score += 0.45
        elif "intro" in sec_low or "conclu" in sec_low:
            score += 0.15
        scored.append((score, idx, chunk))

    scored.sort(key=lambda x: (-x[0], x[1]))
    top = [item[2] for item in scored[:top_k]]
    # Ensure Abstract is included if available and relevant
    abstract_chunks = [c for c in chunks if (c.get("section") or "").lower() == "abstract"]
    if abstract_chunks and abstract_chunks[0] not in top:
        top[-1] = abstract_chunks[0]
    return top


def verify_verbatim_quote(quote: Optional[str], passages: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], bool]:
    """
    Programmatically verifies that evidence_quote is an actual substring of the provided passages
    after whitespace normalization. Returns (verified_quote, matching_passage, was_exact).
    """
    if not quote or not passages:
        return None, passages[0] if passages else None, False

    norm_q = normalize_ws(quote).strip('"\'“” ')
    if len(norm_q) < 12:
        return None, passages[0], False

    # Exact substring check (case-insensitive)
    for p in passages:
        norm_p = normalize_ws(p.get("text", ""))
        idx = norm_p.lower().find(norm_q.lower())
        if idx != -1:
            return norm_p[idx : idx + len(norm_q)], p, True

    # Fuzzy sentence fallback from supplied passages (never invent text!)
    best_sent = None
    best_passage = passages[0]
    best_score = 0.0
    for p in passages:
        norm_p = normalize_ws(p.get("text", ""))
        for sent in re.split(r"(?<=[.!?])\s+", norm_p):
            s = sent.strip()
            if len(s) < 20:
                continue
            sc = fuzz.partial_ratio(norm_q.lower(), s.lower())
            if sc > best_score:
                best_score = sc
                best_sent = s
                best_passage = p

    if best_score >= 82 and best_sent:
        return best_sent, best_passage, True

    return None, best_passage, False


def heuristic_compare_claim(
    claim_text: str,
    passages: List[Dict[str, Any]],
    paper: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic fallback comparison using token overlap, numeric checks, and domain cues."""
    clean_claim = re.sub(r"\[\d+(?:\s*[,;\-–]\s*\d+)*\]", "", claim_text)
    clean_claim = re.sub(r"\([A-Z][^)]*(?:19|20)\d{2}[^)]*\)", "", clean_claim).strip()
    claim_toks = set(tokenize(clean_claim))

    best_sent = None
    best_passage = passages[0] if passages else {"section": "Abstract", "page": 1, "text": ""}
    best_overlap = 0.0

    all_text = " ".join(p.get("text", "") for p in passages)
    all_toks = set(tokenize(all_text))

    for p in passages:
        norm_p = normalize_ws(p.get("text", ""))
        for sent in re.split(r"(?<=[.!?])\s+", norm_p):
            s = sent.strip()
            if len(s) < 20:
                continue
            s_toks = set(tokenize(s))
            if not claim_toks:
                continue
            overlap = len(claim_toks & s_toks) / max(len(claim_toks), 1)
            if overlap > best_overlap:
                best_overlap = overlap
                best_sent = s
                best_passage = p

    doc_overlap = len(claim_toks & all_toks) / max(len(claim_toks), 1)
    claim_nums = [n.lower().strip() for n in NUMBER_RE.findall(clean_claim)]
    missing_nums = [n for n in claim_nums if n not in all_text.lower()]

    flags: List[str] = []
    if paper.get("is_retracted"):
        flags.append("retracted")

    if missing_nums:
        flags.append("number_not_found")

    # Decide verdict heuristically
    if doc_overlap >= 0.55 and not missing_nums:
        verdict = "supported"
        confidence = min(84, int(58 + doc_overlap * 30))
        reason = (
            f"Heuristic overlap ({int(doc_overlap * 100)}%) matches key concepts in the cited paper "
            f"({paper.get('title', 'source')}). Verify exact nuance in the quoted passage."
        )
    elif doc_overlap >= 0.30 and missing_nums:
        verdict = "partly_supported"
        confidence = 58
        flags.append("scope_mismatch")
        reason = (
            f"The cited paper discusses related concepts, but specific quantitative claim(s) ({', '.join(missing_nums)}) "
            f"could not be located in the retrieved passages."
        )
    elif doc_overlap >= 0.32:
        verdict = "partly_supported"
        confidence = 55
        reason = (
            f"Partial lexical overlap ({int(doc_overlap * 100)}%) with the cited source; key details require human review."
        )
    else:
        verdict = "unsupported"
        confidence = 65
        flags.append("reference_mismatch")
        reason = (
            f"Retrieved passages from '{paper.get('title', 'the cited paper')}' do not substantiate this claim "
            f"(lexical overlap only {int(doc_overlap * 100)}%). Possible reference mismatch or unsupported assertion."
        )

    evidence_level = paper.get("evidence_level", "abstract_only")
    note = "Evaluated in heuristic fallback mode (keyword/BM25 similarity)."
    if evidence_level == "abstract_only":
        confidence = min(confidence, 68)
        note += " Only the abstract was available."

    return {
        "verdict": verdict,
        "reason": reason,
        "evidence_quote": best_sent,
        "evidence_passage": best_passage.get("text", ""),
        "evidence_location": {"section": best_passage.get("section", "Abstract"), "page": best_passage.get("page", 1)},
        "confidence": confidence,
        "confidence_note": note,
        "flags": sorted(set(flags)),
        "used_gemini": False,
    }


def find_best_matching_reference(
    claim_text: str,
    resolved_map: Dict[int, Dict[str, Any]],
    found_map: Dict[int, bool],
) -> Optional[int]:
    """
    For student reports / case studies that list references at the end without inline [1] markers,
    finds the best-matching retrieved reference in the document using token overlap against
    each reference's title, abstract, and chunks.
    """
    q_toks = set(tokenize(claim_text))
    if not q_toks:
        return None

    best_idx: Optional[int] = None
    best_score = 0.0

    for idx, paper in resolved_map.items():
        if not found_map.get(idx) or not paper.get("title"):
            continue
        chunks = paper.get("chunks") or []
        title_toks = set(tokenize(paper.get("title", "")))
        chunk_best = 0.0
        for ch in chunks[:10]:
            c_toks = set(tokenize(ch.get("text", "")))
            if c_toks:
                ov = len(q_toks & c_toks) / max(len(q_toks), 1)
                if ov > chunk_best:
                    chunk_best = ov
        title_ov = len(q_toks & title_toks) / max(len(q_toks), 1)
        # Prefer references that actually have text chunks
        score = max(chunk_best, title_ov * 0.85) + (0.08 if chunks else 0.0)
        if score > best_score:
            best_score = score
            best_idx = idx

    # Require meaningful lexical overlap (>= 20% or >= 2 shared tokens)
    if best_idx is not None and best_score >= 0.22:
        return best_idx
    return None


async def compare_claim_with_source(
    claim_text: str,
    paper: Dict[str, Any],
    other_papers_summary: str = "",
) -> Dict[str, Any]:
    """
    Stage 5: Selects top 3 passages from the cited paper, calls Gemini with strict JSON schema
    and few-shot calibration, verifies evidence_quote verbatim, applies confidence & retraction rules.
    """
    chunks = paper.get("chunks") or []
    if not chunks and paper.get("abstract"):
        chunks = [{"section": "Abstract", "page": 1, "text": paper["abstract"]}]

    if not chunks:
        flags = ["metadata_only", "needs_manual_review"]
        if paper.get("is_retracted"):
            flags.append("retracted")
        title_str = paper.get("title") or "the cited source"
        return {
            "verdict": "partly_supported",
            "reason": (
                f"The cited source '{title_str}' exists in scholarly records, but neither an abstract nor "
                f"open-access full text could be retrieved (likely paywalled or a book/standard). "
                f"Cannot confirm or refute automatically — please verify against the original source."
            ),
            "evidence_quote": None,
            "evidence_passage": None,
            "evidence_location": {"section": "Metadata Only", "page": 1},
            "confidence": 35,
            "confidence_note": "Paper metadata verified, but source text is paywalled/unavailable via open APIs; manual review required.",
            "flags": sorted(set(flags)),
            "used_gemini": False,
        }

    top_passages = select_top_passages(claim_text, chunks, top_k=3)
    passages_block = "\n\n".join(
        f"[PASSAGE {i+1} | Section: {p.get('section', 'Body')} | Page: {p.get('page', 1)}]\n{p.get('text', '')}"
        for i, p in enumerate(top_passages)
    )

    evidence_level = paper.get("evidence_level", "abstract_only")
    paper_year = paper.get("year")

    prompt = f"""You are a rigorous scientific citation verifier. Compare the CLAIM strictly against ONLY the supplied SOURCE PASSAGES from the cited paper.

RULES:
1. Use ONLY the supplied passages below — NEVER rely on outside knowledge to claim support that is not written in the passages.
2. If the passages do not contain the claimed result, statistic, or method, return "unsupported" or "partly_supported" with a clear reason. Never invent support.
3. "evidence_quote" MUST be copied EXACTLY VERBATIM (word-for-word substring) from one of the supplied passages, or null if no passage relates to the claim.
4. Use verdict:
   - "supported": the passages clearly and accurately substantiate the claim (including numbers/scope).
   - "partly_supported": the cited paper is about the right model/subject and mentions the topic, a related improvement, or the target modality (even as future work or on a different benchmark), BUT omits or overstates the specific claimed number/percentage or experimental scope (set flags "number_not_found" and/or "scope_mismatch", and quote the passage showing the paper's actual scope!).
   - "unsupported": the passages do not support the claimed mechanism/finding at all, or the claim is misattributed to the wrong paper (set flag "reference_mismatch").
   - "contradictory": the passages directly state an opposing number or conclusion (e.g., claiming 99.9% accuracy when the paper reports 19% error).
   - "possibly_outdated": the paper is older (e.g. >7 years old) AND the claim makes a current/state-of-the-art assertion that may be superseded.
5. Important calibration: If the claim refers to the right paper's core system/model AND the passages discuss related performance or mention the target domain (e.g., images as future work) without reporting the claimed statistic (like "30%"), classify as "partly_supported" (needs human review) rather than "unsupported", and provide the verbatim passage showing what the paper actually says.
6. Set flags from: ["reference_mismatch", "missing_reference", "retracted", "scope_mismatch", "number_not_found", "outdated"].

FEW-SHOT EXAMPLE:
Claim: "A particular study found that a learning app improved test scores by 30%."
Supplied passage: "In a small pilot with 24 students, participants using the mobile learning app showed modest score gains compared to baseline, though no exact percentage improvement was reported."
Expected JSON:
{{
  "verdict": "partly_supported",
  "reason": "The cited pilot study reports modest test score gains from the learning app, but it does not report a 30% improvement figure and only tested a small pilot cohort.",
  "evidence_quote": "In a small pilot with 24 students, participants using the mobile learning app showed modest score gains compared to baseline, though no exact percentage improvement was reported.",
  "evidence_location": {{"section": "Results", "page": 4}},
  "confidence": 82,
  "confidence_note": "Full passage checked; the claimed 30% figure is absent from the source.",
  "flags": ["number_not_found", "scope_mismatch"]
}}

NOW EVALUATE THIS CLAIM:
Cited paper: "{paper.get('title', 'Unknown')}" ({paper_year or 'n.d.'})
Evidence level available: {evidence_level}
Other references in the user's document (for spotting reference mismatches only): {other_papers_summary or 'None'}

CLAIM:
"{claim_text}"

SUPPLIED SOURCE PASSAGES:
{passages_block}

Return strict JSON matching this exact schema:
{{
  "verdict": "supported" | "partly_supported" | "unsupported" | "contradictory" | "possibly_outdated",
  "reason": "1-3 sentence plain-language explanation",
  "evidence_quote": "EXACT verbatim substring from the supplied passages, or null",
  "evidence_location": {{"section": "section name", "page": 1}},
  "confidence": 0-100,
  "confidence_note": "brief note explaining certainty or limitations",
  "flags": []
}}
"""
    llm_resp = await gemini_client.generate_json(
        prompt,
        system_instruction="You are PaperProof's automated scientific evidence checker. Strictly ground every verdict in the supplied passages. Output valid JSON only.",
    )

    if not isinstance(llm_resp, dict) or llm_resp.get("verdict") not in VALID_VERDICTS:
        return heuristic_compare_claim(claim_text, top_passages, paper)

    verdict = llm_resp["verdict"]
    reason = str(llm_resp.get("reason") or "Automated comparison completed.").strip()
    raw_quote = llm_resp.get("evidence_quote")
    try:
        confidence = int(llm_resp.get("confidence", 70))
    except Exception:
        confidence = 70
    confidence = max(5, min(99, confidence))
    confidence_note = str(llm_resp.get("confidence_note") or "").strip()
    flags = [str(f) for f in (llm_resp.get("flags") or []) if isinstance(f, str)]

    # Programmatic verbatim quote verification
    verified_quote, matched_passage, was_exact = verify_verbatim_quote(raw_quote, top_passages)
    if raw_quote and not was_exact:
        confidence = max(20, confidence - 15)
        if confidence_note:
            confidence_note += " Quote could not be matched verbatim and was omitted."
        else:
            confidence_note = "Proposed quote failed verbatim substring check and was omitted."

    ev_loc = llm_resp.get("evidence_location") if isinstance(llm_resp.get("evidence_location"), dict) else {}
    if matched_passage:
        ev_loc = {
            "section": matched_passage.get("section") or ev_loc.get("section") or "Body",
            "page": matched_passage.get("page") or ev_loc.get("page") or 1,
        }
    else:
        ev_loc = {"section": ev_loc.get("section") or "Abstract", "page": ev_loc.get("page") or 1}

    # Blend raw LLM confidence slightly with lexical grounding so scores reflect actual evidence strength
    # instead of collapsing to identical numbers across claims
    matched_text = (matched_passage.get("text", "") if matched_passage else "") or (
        top_passages[0].get("text", "") if top_passages else ""
    )
    claim_toks = set(tokenize(claim_text))
    passage_toks = set(tokenize(matched_text))
    lex_overlap = (len(claim_toks & passage_toks) / max(len(claim_toks), 1)) if claim_toks else 0.5
    if verdict == "supported":
        # Small grounded adjustment (-6 to +3) based on how directly the claim's terms appear in the passage
        adj = int(round((lex_overlap - 0.55) * 14))
        confidence = max(45, min(98, confidence + max(-7, min(3, adj))))
    elif verdict == "partly_supported":
        # Partly supported claims inherently carry more uncertainty than full support
        confidence = min(confidence, 82)
        adj = int(round((lex_overlap - 0.50) * 10))
        confidence = max(35, min(82, confidence + max(-6, min(4, adj))))

    # Apply smooth proportional discount when only the abstract was available
    # (preserves differentiation between claims instead of flattening all of them to a single constant)
    if evidence_level == "abstract_only":
        confidence = max(25, min(86, int(round(confidence * 0.85))))
        if "abstract" not in confidence_note.lower():
            suffix = "Only the abstract was available; full-text methods and exact figures could not be checked."
            confidence_note = f"{confidence_note} {suffix}".strip()

    # Check retraction from metadata
    if paper.get("is_retracted") and "retracted" not in flags:
        flags.append("retracted")
        confidence_note = f"WARNING: Cited paper is marked as retracted in scholarly metadata. {confidence_note}".strip()

    # Check possibly_outdated heuristic for old papers (>9 years old) + time-sensitive claim
    cutoff_year = datetime.now().year - 9
    if paper_year and isinstance(paper_year, int) and paper_year <= cutoff_year and TIME_SENSITIVE_RE.search(claim_text):
        if "outdated" not in flags:
            flags.append("outdated")
        if verdict == "supported":
            verdict = "possibly_outdated"
            reason += f" Note: the cited source is from {paper_year} and may be superseded for this time-sensitive claim."

    if not confidence_note:
        confidence_note = "Checked against retrieved source passages."

    return {
        "verdict": verdict,
        "reason": reason,
        "evidence_quote": verified_quote,
        "evidence_passage": matched_passage.get("text", "") if matched_passage else (top_passages[0].get("text", "") if top_passages else None),
        "evidence_location": ev_loc,
        "confidence": confidence,
        "confidence_note": confidence_note,
        "flags": sorted(set(flags)),
        "used_gemini": True,
    }
