import io
import os
import re
from typing import Dict, List, Tuple
from pypdf import PdfReader
from docx import Document


class IngestError(Exception):
    """Base error during document ingestion."""


class ScannedPDFError(IngestError):
    """Raised when a PDF contains pages but no extractable text layer."""


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "document.txt")
    clean = re.sub(r"[^A-Za-z0-9._\-\s()]", "_", base).strip()
    if not clean:
        clean = "document.txt"
    return clean[:180]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Fix hyphenated line breaks typical in PDFs
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Collapse excessive spaces while preserving paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages_from_bytes(content: bytes, filename: str) -> List[Dict]:
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise IngestError(
            f"Unsupported file type '{ext}'. Please upload a PDF, DOCX, or TXT document."
        )

    if ext == ".txt":
        try:
            raw = content.decode("utf-8")
        except UnicodeDecodeError:
            raw = content.decode("latin-1", errors="replace")
        cleaned = clean_text(raw)
        if len(cleaned) < 20:
            raise IngestError("The uploaded text file is empty or too short to verify.")
        return [{"page": 1, "text": cleaned}]

    if ext == ".docx":
        try:
            from docx.document import Document as DocxDocument
            from docx.oxml.table import CT_Tbl
            from docx.oxml.text.paragraph import CT_P
            from docx.table import Table
            from docx.text.paragraph import Paragraph

            doc = Document(io.BytesIO(content))
            blocks: List[str] = []
            # Walk body elements in true document order so tables don't get dumped after References
            for child in doc.element.body.iterchildren():
                if isinstance(child, CT_P):
                    txt = Paragraph(child, doc).text.strip()
                    if txt:
                        blocks.append(txt)
                elif isinstance(child, CT_Tbl):
                    table = Table(child, doc)
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            blocks.append(row_text)
            full_text = clean_text("\n\n".join(blocks))
        except Exception as exc:
            raise IngestError(f"Could not parse DOCX file: {exc}") from exc

        if len(full_text) < 20:
            raise IngestError("The DOCX file contains no readable text.")
        # Approximate pages every ~3200 characters (splitting cleanly at paragraph boundaries)
        pages = []
        chunk_size = 3200
        cur_buf: List[str] = []
        cur_len = 0
        page_num = 1
        for para in full_text.split("\n\n"):
            if cur_buf and cur_len + len(para) + 2 > chunk_size:
                pages.append({"page": page_num, "text": "\n\n".join(cur_buf)})
                page_num += 1
                cur_buf, cur_len = [para], len(para)
            else:
                cur_buf.append(para)
                cur_len += len(para) + 2
        if cur_buf:
            pages.append({"page": page_num, "text": "\n\n".join(cur_buf)})
        return pages

    # PDF extraction with page numbers
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise IngestError(f"Could not open PDF file (it may be corrupted or encrypted): {exc}") from exc

    if len(reader.pages) == 0:
        raise IngestError("The uploaded PDF contains zero pages.")

    pages: List[Dict] = []
    total_chars = 0
    for idx, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        cleaned = clean_text(txt)
        total_chars += len(cleaned)
        pages.append({"page": idx, "text": cleaned})

    if total_chars < 40:
        raise ScannedPDFError(
            "This PDF appears to be an image-only / scanned document with no selectable text layer. "
            "PaperProof cannot read scanned images directly yet — please run OCR (e.g., Adobe Acrobat, "
            "Google Drive, or ocrmypdf) or paste the text directly into the text box."
        )

    return pages


def extract_pages_from_text(text: str) -> List[Dict]:
    cleaned = clean_text(text)
    if len(cleaned) < 20:
        raise IngestError("Please provide at least a short paragraph of academic text to verify.")
    return [{"page": 1, "text": cleaned}]


REF_HEADING_RE = re.compile(
    r"(?im)^[ \t]*(?:(?:chapter|section|part|unit)[ \t]+(?:[IVXLCDM]+|\d+)[ \t]*[:.\-–]?[ \t]*|\d+(?:\.\d+)*\.?[ \t]+)?"
    r"(references?(?:[ \t]*(?:&|and)[ \t]*(?:bibliography|links|sources))?|bibliography|works[ \t]+cited|"
    r"literature[ \t]+cited|cited[ \t]+references?|web[ \t]+references?)[ \t]*:?[ \t]*$"
)

POST_REF_HEADING_RE = re.compile(
    r"(?im)^[ \t]*(?:(?:chapter|section|part)[ \t]+(?:[IVXLCDM]+|\d+)[ \t]*[:.\-–]?[ \t]*|\d+(?:\.\d+)*\.?[ \t]+)?"
    r"(appendix(?:\s*[A-Z0-9\s/:\-–]*)?|annexure(?:\s*[A-Z0-9\s/:\-–]*)?|appendices|list[ \t]+of[ \t]+(?:figures|tables)|"
    r"author[ \t]+biograph(?:y|ies)|biograph(?:y|ies)|certificate|declaration|plagiarism[ \t]+report)[ \t]*:?[ \t]*$"
)


def split_body_and_references(pages: List[Dict]) -> Tuple[List[Dict], str]:
    """
    Splits extracted pages into body pages (preserving page numbers) and a single references string.
    Handles standard journal papers AND student mini-project / thesis reports
    (e.g. 'CHAPTER 7: REFERENCE', trailing 'CHAPTER 8: APPENDIX / ANNEXURE', TOC lines).
    """
    matches = []
    for p_idx, page in enumerate(pages):
        txt = page.get("text", "")
        for m in REF_HEADING_RE.finditer(txt):
            # Ignore Table of Contents lines or headings inside early index pages when a later heading exists
            line_text = m.group(0)
            if "|" in line_text:
                continue
            matches.append((p_idx, m.start(), m.end()))

    if not matches:
        # Fallback: look for a References heading followed inline by [1] or author entry
        inline_re = re.compile(
            r"(?im)(?:^|\n)[ \t]*(?:(?:chapter|section)[ \t]+\d+[ \t]*[:.\-–]?[ \t]*|\d+\.?[ \t]+)?(references?|bibliography|works cited)[ \t]*:?[ \t]*(?:\n|$)"
        )
        for p_idx, page in enumerate(pages):
            for m in inline_re.finditer(page.get("text", "")):
                matches.append((p_idx, m.start(), m.end()))

    if not matches:
        return pages, ""

    # Prefer the last match that actually has content after it (skips TOC lines and empty trailing mentions)
    chosen = matches[-1]
    for cand in reversed(matches):
        p_idx, s_pos, e_pos = cand
        after_here = pages[p_idx].get("text", "")[e_pos:].strip()
        after_later = "".join(p.get("text", "").strip() for p in pages[p_idx + 1 :])
        if len(after_here) + len(after_later) >= 35:
            chosen = cand
            break

    split_p_idx, start_pos, end_pos = chosen
    body_pages: List[Dict] = []
    ref_parts: List[str] = []

    for i, page in enumerate(pages):
        txt = page.get("text", "")
        if i < split_p_idx:
            if txt.strip():
                body_pages.append({"page": page["page"], "text": txt})
        elif i == split_p_idx:
            before = txt[:start_pos].strip()
            after = txt[end_pos:].strip()
            if before:
                body_pages.append({"page": page["page"], "text": before})
            if after:
                ref_parts.append(after)
        else:
            if txt.strip():
                ref_parts.append(txt)

    refs_combined = "\n\n".join(ref_parts).strip()

    # Stop collecting references if an Appendix / Annexure / next Chapter starts after References
    post_m = POST_REF_HEADING_RE.search(refs_combined)
    if post_m and post_m.start() > 20:
        refs_combined = refs_combined[: post_m.start()].strip()

    return body_pages, refs_combined
