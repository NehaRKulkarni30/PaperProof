"""Unit tests for PaperProof's 6-stage verification pipeline and anti-hallucination guardrails."""

import asyncio
import io
import os
import sys

import pytest
from docx import Document

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import resolve_database_url
from app.pipeline.claims import (
    expand_numeric_markers,
    extract_markers_from_text,
    find_narrative_reference_matches,
    heuristic_extract_claims,
    map_marker_to_reference,
)
from app.pipeline.compare import (
    compare_claim_with_source,
    find_best_matching_reference,
    heuristic_compare_claim,
    select_top_passages,
    verify_verbatim_quote,
)
from app.pipeline.ingest import (
    IngestError,
    extract_pages_from_bytes,
    extract_pages_from_text,
    sanitize_filename,
    split_body_and_references,
)
from app.pipeline.references import (
    extract_identifiers,
    heuristic_parse_reference,
    split_reference_entries,
)
from app.pipeline.retrieve import (
    _html_to_chunks,
    _is_non_scholarly_url,
    _is_safe_public_url,
    compute_match_score,
    reconstruct_openalex_abstract,
)


# ---------------------------------------------------------------------------
# Stage 1: Ingest & Split
# ---------------------------------------------------------------------------

def test_sanitize_filename_strips_traversal_and_special_chars():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("My Report (Final)!.pdf") == "My Report (Final)_.pdf"
    assert sanitize_filename("") == "document.txt"


def test_extract_pages_rejects_unsupported_and_short_text():
    with pytest.raises(IngestError):
        extract_pages_from_bytes(b"hello world", "malicious.exe")
    with pytest.raises(IngestError):
        extract_pages_from_text("too short")


def test_split_body_and_references_handles_student_chapter_heading_and_appendix():
    pages = [
        {"page": 1, "text": "CONTENTS\n7 | References\n8 | Appendix"},
        {
            "page": 2,
            "text": (
                "CHAPTER 2: LITERATURE REVIEW\n"
                "Folianto et al. proposed a SmartBin system for waste monitoring.\n\n"
                "CHAPTER 7: REFERENCE\n"
                '[1] S. Longhi, "Solid Waste Management Architecture," IEEE, 2012.\n'
                '[2] M. Folianto, "Smartbin: Smart Waste Management System," IEEE, 2015.\n\n'
                "CHAPTER 8: APPENDIX / ANNEXURE\n"
                "8.1 Arduino Code\nvoid setup() {}"
            ),
        },
    ]
    body_pages, refs_text = split_body_and_references(pages)
    assert len(body_pages) == 2
    assert "Folianto et al." in body_pages[1]["text"]
    assert "CHAPTER 7: REFERENCE" not in body_pages[1]["text"]
    assert "[1] S. Longhi" in refs_text
    assert "[2] M. Folianto" in refs_text
    assert "void setup()" not in refs_text


def test_docx_extraction_preserves_table_and_paragraph_order():
    doc = Document()
    doc.add_paragraph("CHAPTER 1: INTRODUCTION\nThis is a real-time IoT monitoring report.")
    tbl = doc.add_table(rows=2, cols=2)
    tbl.cell(0, 0).text = "Component"
    tbl.cell(0, 1).text = "Qty"
    tbl.cell(1, 0).text = "ESP8266"
    tbl.cell(1, 1).text = "1"
    doc.add_paragraph("CHAPTER 7: REFERENCE")
    doc.add_paragraph('[1] M. Folianto, "Smartbin: Smart Waste Management System," IEEE, 2015.')

    buf = io.BytesIO()
    doc.save(buf)
    pages = extract_pages_from_bytes(buf.getvalue(), "Student_Mini_Project.docx")
    body_pages, refs_text = split_body_and_references(pages)

    body_all = "\n".join(p["text"] for p in body_pages)
    assert "ESP8266 | 1" in body_all
    assert "ESP8266" not in refs_text
    assert "Smartbin" in refs_text


# ---------------------------------------------------------------------------
# Stage 2: Reference Parsing
# ---------------------------------------------------------------------------

def test_extract_identifiers_finds_doi_arxiv_and_url():
    raw = "Vaswani et al. (2017). Attention Is All You Need. arXiv:1706.03762v7 doi:10.48550/arXiv.1706.03762 https://arxiv.org/abs/1706.03762"
    ids = extract_identifiers(raw)
    assert ids["arxiv_id"] == "1706.03762"
    assert ids["doi"] == "10.48550/arXiv.1706.03762"
    assert ids["url"] == "https://arxiv.org/abs/1706.03762"


def test_heuristic_parse_ieee_quoted_title():
    raw = '[2] M. Folianto, Y. S. Low, and W. L. Yeow, "Smartbin: Smart Waste Management System," IEEE ISSNIP, Singapore, pp. 1-2, 2015.'
    parsed = heuristic_parse_reference("[2]", raw)
    assert parsed["title"] == "Smartbin: Smart Waste Management System"
    assert parsed["year"] == 2015
    assert any("Folianto" in a for a in parsed["authors"])


def test_split_reference_entries_numeric_and_author_year():
    numeric = "[1] Paper A, 2017.\n[2] Paper B, 2019."
    entries = split_reference_entries(numeric)
    assert [m for m, _ in entries] == ["[1]", "[2]"]

    ay = "Nuvolari, A. [2005]. Open Source Software Development.\nShort, S. [2011]. Locomotive to Aeromotive."
    ay_entries = split_reference_entries(ay)
    assert len(ay_entries) == 2


# ---------------------------------------------------------------------------
# Stage 3: Claim Extraction & Citation Mapping
# ---------------------------------------------------------------------------

def test_marker_extraction_expands_ranges_and_ignores_years():
    assert expand_numeric_markers("1, 3-5") == ["[1]", "[3]", "[4]", "[5]"]
    # 4-digit years like [1910] must NOT be parsed as numeric reference #1910
    assert expand_numeric_markers("1910") == []
    markers = extract_markers_from_text("Brockett [1910] and Vaswani et al. (Vaswani et al., 2017) [1, 2].")
    assert "[1]" in markers
    assert "[2]" in markers
    assert "(Vaswani et al., 2017)" in markers
    assert "(Brockett, 1910)" in markers
    assert "[1910]" not in markers


def test_narrative_reference_matching_for_student_literature_reviews():
    parsed_refs = [
        {"marker": "[1]", "raw_text": 'S. Longhi, "Solid Waste Management Architecture"', "parsed": {"authors": ["S. Longhi"], "title": "Solid Waste Management Architecture", "year": 2012}},
        {"marker": "[2]", "raw_text": 'M. Folianto, "Smartbin: Smart Waste Management System"', "parsed": {"authors": ["M. Folianto"], "title": "Smartbin: Smart Waste Management System", "year": 2015}},
    ]
    hits = find_narrative_reference_matches(
        "Folianto et al. proposed a SmartBin system that uses sensors to monitor garbage levels.",
        parsed_refs,
    )
    assert hits == [1]
    assert map_marker_to_reference("[2]", parsed_refs) == 1
    assert map_marker_to_reference("[99]", parsed_refs) is None


def test_heuristic_extract_claims_skips_student_boilerplate():
    pages = [
        {
            "page": 1,
            "text": (
                "Certified that the MINI PROJECT entitled Smart Waste Management is carried out by bonafide student.\n"
                "The Transformer relies entirely on attention mechanisms instead of recurrence [1]."
            ),
        }
    ]
    claims = heuristic_extract_claims(pages)
    assert len(claims) == 1
    assert "Transformer" in claims[0]["text"]


# ---------------------------------------------------------------------------
# Stage 4: Retrieval Utilities & SSRF Protection
# ---------------------------------------------------------------------------

def test_compute_match_score_and_openalex_abstract_reconstruction():
    parsed = {"title": "Attention Is All You Need", "year": 2017}
    exact = {"title": "Attention Is All You Need", "year": 2017}
    wrong = {"title": "Deep Residual Learning for Image Recognition", "year": 2015}
    assert compute_match_score(parsed, exact) >= 95.0
    assert compute_match_score(parsed, wrong) < 50.0

    inv = {"Attention": [0], "is": [1], "all": [2], "you": [3], "need.": [4]}
    assert reconstruct_openalex_abstract(inv) == "Attention is all you need."


def test_ssrf_guard_blocks_private_and_local_urls():
    assert _is_safe_public_url("http://127.0.0.1:8000/api/health") is False
    assert _is_safe_public_url("http://localhost/admin") is False
    assert _is_safe_public_url("http://169.254.169.254/latest/meta-data/") is False
    assert _is_safe_public_url("http://10.0.0.5/internal") is False
    assert _is_safe_public_url("file:///etc/passwd") is False
    assert _is_non_scholarly_url("https://www.energy.gov/eere/vehicles/batteries") is True
    assert _is_non_scholarly_url("https://arxiv.org/abs/1706.03762") is False


def test_html_to_chunks_strips_scripts_and_keeps_prose():
    html = """
    <html><head><title>EV Batteries</title><script>alert(1);</script></head>
    <body><nav>Home | Menu</nav><article>
    <p>Battery electric vehicles use rechargeable lithium-ion battery packs to power electric motors with zero tailpipe emissions.</p>
    </article></body></html>
    """
    chunks = _html_to_chunks(html, "EV Batteries")
    assert len(chunks) == 1
    assert "lithium-ion" in chunks[0]["text"]
    assert "alert(1)" not in chunks[0]["text"]


# ---------------------------------------------------------------------------
# Stage 5: BM25, Anti-Hallucination Quote Verification & Comparison
# ---------------------------------------------------------------------------

def test_bm25_select_top_passages_ranks_relevant_chunk_first():
    chunks = [
        {"section": "Related Work", "page": 2, "text": "Convolutional networks are popular for computer vision tasks."},
        {"section": "Model Architecture", "page": 3, "text": "The Transformer dispenses with recurrence and convolutions entirely, relying solely on attention mechanisms."},
        {"section": "Training", "page": 5, "text": "We used the Adam optimizer with beta1 = 0.9 and beta2 = 0.98."},
        {"section": "Conclusion", "page": 9, "text": "We plan to extend attention models to images and audio in future work."},
    ]
    top = select_top_passages("The Transformer relies entirely on attention mechanisms instead of recurrence.", chunks, top_k=2)
    assert len(top) == 2
    assert "dispenses with recurrence" in top[0]["text"]


def test_verify_verbatim_quote_accepts_exact_and_rejects_hallucinated():
    passages = [
        {
            "section": "Abstract",
            "page": 1,
            "text": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        }
    ]
    exact_q, matched_p, was_exact = verify_verbatim_quote(
        "based solely on attention mechanisms, dispensing with recurrence and convolutions entirely",
        passages,
    )
    assert was_exact is True
    assert exact_q is not None
    assert matched_p["section"] == "Abstract"

    fake_q, _, fake_exact = verify_verbatim_quote(
        "Our experiments prove a 99% speedup on quantum biological folding datasets",
        passages,
    )
    assert fake_exact is False
    assert fake_q is None


def test_heuristic_compare_and_paywall_metadata_only():
    passages = [
        {
            "section": "Abstract",
            "page": 1,
            "text": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        }
    ]
    paper = {"title": "Attention Is All You Need", "evidence_level": "full_text", "is_retracted": False}

    supported = heuristic_compare_claim(
        "The Transformer architecture relies solely on attention mechanisms and dispenses with recurrence [1].",
        passages,
        paper,
    )
    assert supported["verdict"] == "supported"

    missing_num = heuristic_compare_claim(
        "The Transformer architecture improved image classification accuracy by 30% [1].",
        passages,
        paper,
    )
    assert missing_num["verdict"] in ("partly_supported", "unsupported")
    assert "number_not_found" in missing_num["flags"]

    # Paywalled / metadata-only paper should not be harshly marked 'unsupported'
    paywalled = {"title": "ISO 6469 Safety Specifications", "chunks": [], "abstract": "", "is_retracted": False}
    res = asyncio.run(compare_claim_with_source("ISO 6469 defines EV electrical safety.", paywalled))
    assert res["verdict"] == "partly_supported"
    assert "metadata_only" in res["flags"]
    assert "needs_manual_review" in res["flags"]


def test_find_best_matching_reference_for_bibliography_at_end_reports():
    resolved_map = {
        0: {
            "title": "How Do All-Electric Cars Work?",
            "chunks": [{"text": "All-electric vehicles run on electricity stored in rechargeable battery packs and produce zero tailpipe emissions."}],
        },
        1: {
            "title": "Smartbin: Smart Waste Management System",
            "chunks": [{"text": "Ultrasonic sensors measure garbage bin fill levels in smart cities."}],
        },
    }
    found_map = {0: True, 1: True}
    idx = find_best_matching_reference(
        "Battery electric vehicles run on rechargeable battery packs and produce zero tailpipe emissions.",
        resolved_map,
        found_map,
    )
    assert idx == 0


def test_resolve_database_url_handles_vercel_postgres_and_sqlite():
    # Local default stays SQLite
    assert resolve_database_url("sqlite:///./paperproof.db", env={}) == "sqlite:///./paperproof.db"
    # Vercel without Postgres falls back to writable /tmp SQLite
    assert resolve_database_url("sqlite:///./paperproof.db", env={"VERCEL": "1"}) == "sqlite:////tmp/paperproof.db"
    # Vercel with Neon POSTGRES_URL normalizes to psycopg v3
    pg = resolve_database_url(
        "sqlite:///./paperproof.db",
        env={"VERCEL": "1", "POSTGRES_URL": "postgres://user:pass@ep-cool.neon.tech/neondb?sslmode=require&pgbouncer=true"},
    )
    assert pg == "postgresql+psycopg://user:pass@ep-cool.neon.tech/neondb?sslmode=require"
    # Explicit postgresql:// DATABASE_URL normalizes cleanly
    pg2 = resolve_database_url("postgresql://u:p@host:5432/mydb", env={})
    assert pg2 == "postgresql+psycopg://u:p@host:5432/mydb"
