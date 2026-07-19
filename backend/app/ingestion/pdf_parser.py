"""
Born-digital PDF text extraction — Phase 3 (PDF-only slice).

Primary extractor: PyMuPDF (fitz) — fast, good layout handling.
Fallback: pdfplumber — used only if PyMuPDF returns suspiciously little text
for a file that intake.py already determined isn't scanned (e.g. a PDF with
unusual encoding that trips up one library but not the other).

Does NOT do OCR. Does NOT do entity extraction. Just: file in, clean text out.
"""

from dataclasses import dataclass, field

import fitz  # PyMuPDF
import pdfplumber


@dataclass
class ParsedPage:
    page_number: int  # 1-indexed
    text: str


@dataclass
class ParsedDocument:
    filename: str
    page_count: int
    full_text: str
    pages: list[ParsedPage] = field(default_factory=list)
    extractor_used: str = "pymupdf"


def _parse_with_pymupdf(filepath) -> ParsedDocument:
    doc = fitz.open(filepath)
    pages = []
    for i in range(doc.page_count):
        text = doc[i].get_text()
        pages.append(ParsedPage(page_number=i + 1, text=text))
    doc.close()
    full_text = "\n\n".join(p.text for p in pages)
    return ParsedDocument(
        filename=str(filepath),
        page_count=len(pages),
        full_text=full_text,
        pages=pages,
        extractor_used="pymupdf",
    )


def _parse_with_pdfplumber(filepath) -> ParsedDocument:
    pages = []
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages.append(ParsedPage(page_number=i + 1, text=text))
    full_text = "\n\n".join(p.text for p in pages)
    return ParsedDocument(
        filename=str(filepath),
        page_count=len(pages),
        full_text=full_text,
        pages=pages,
        extractor_used="pdfplumber",
    )


# Below this total character count, PyMuPDF's result is treated as
# suspiciously thin and worth a pdfplumber retry before giving up.
MIN_ACCEPTABLE_TEXT_LENGTH = 80


def parse_pdf(filepath) -> ParsedDocument:
    """Extract text from a born-digital PDF. Tries PyMuPDF first; falls back
    to pdfplumber if the result looks too thin to be real. Raises if both
    extractors come back near-empty — that almost certainly means intake.py's
    scanned-PDF check should have caught this file, and it's worth checking
    why it didn't."""
    result = _parse_with_pymupdf(filepath)

    if len(result.full_text.strip()) < MIN_ACCEPTABLE_TEXT_LENGTH:
        fallback = _parse_with_pdfplumber(filepath)
        if len(fallback.full_text.strip()) > len(result.full_text.strip()):
            result = fallback

    if len(result.full_text.strip()) < MIN_ACCEPTABLE_TEXT_LENGTH:
        raise ValueError(
            f"{filepath}: both PyMuPDF and pdfplumber extracted almost no "
            f"text. This file likely needs OCR (not built yet) — check "
            f"intake.py's is_scanned_pdf() result for it."
        )

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.ingestion.pdf_parser <path-to-pdf>")
        sys.exit(1)

    parsed = parse_pdf(sys.argv[1])
    print(f"Extractor used : {parsed.extractor_used}")
    print(f"Page count     : {parsed.page_count}")
    print(f"Total chars    : {len(parsed.full_text)}")
    print("\n--- First 500 characters ---\n")
    print(parsed.full_text[:500])
