"""
Ingestion intake — Phase 3 (PDF + OCR + DOCX slice).

Scope right now, on purpose:
- PDF (born-digital + scanned via OCR) and DOCX are handled.
- Spreadsheets are NOT built yet — this file flags those cases clearly
  rather than silently skipping or crashing on them.
- No LLM entity extraction here. That's a separate later step (needs an API
  key you don't have wired in yet). This module only discovers files and
  classifies which parser each one needs.

Folder → doc_type mapping mirrors docs/source_documents_mapping.md and
docs/data_model_conventions.md. doc_type is a free TEXT column in Postgres
(not an enum), so adding a new folder/type later is safe.
"""

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from app.config import SOURCE_DOCUMENTS_DIR

FOLDER_TO_DOC_TYPE = {
    "safety_policies": "policy",
    "sops": "procedure",
    "emergency_procedures": "emergency_plan",
    "ppe_policy": "ppe_policy",
    "permit_to_work": "permit_to_work",
    "admin_docs": "admin",
    "oem_manuals": "oem_manual",
    "incidents": "incident",
    "work_order": "work_order",
}

# Minimum characters of extracted text on page 1 before we trust a PDF has a
# real text layer. Below this, it's almost certainly a scanned image PDF and
# needs OCR rather than the direct text parser.
SCANNED_TEXT_THRESHOLD = 40

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".csv"}

# What pipeline.py should do with this file:
#   "pdf_born_digital" -> pdf_parser.parse_pdf()
#   "pdf_scanned"       -> ocr_parser.parse_scanned_pdf()
#   "docx"              -> docx_parser.parse_docx()
#   "spreadsheet"       -> spreadsheet_parser.parse_spreadsheet()
FILE_KIND_PDF_BORN_DIGITAL = "pdf_born_digital"
FILE_KIND_PDF_SCANNED = "pdf_scanned"
FILE_KIND_DOCX = "docx"
FILE_KIND_SPREADSHEET = "spreadsheet"


@dataclass
class IntakeResult:
    filepath: Path
    filename: str
    doc_type: str
    file_kind: str  # one of the FILE_KIND_* constants above


def discover_source_files(root: str | None = None) -> list[Path]:
    """Recursively find every supported file (.pdf, .docx) under
    source_documents/ (or a given root)."""
    root_path = Path(root or SOURCE_DOCUMENTS_DIR)
    if not root_path.exists():
        return []
    files = [
        p for p in root_path.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files)


def detect_doc_type(filepath: Path) -> str:
    """Infer doc_type from the immediate parent folder name. Falls back to
    'unknown' for anything not in the mapping (e.g. a file dropped directly
    into source_documents/ with no subfolder) rather than guessing."""
    folder_name = filepath.parent.name
    return FOLDER_TO_DOC_TYPE.get(folder_name, "unknown")


def is_scanned_pdf(filepath: Path) -> bool:
    """Cheap heuristic: try pulling text from the first page. Very little or
    no text means this is almost certainly a scanned image, not a
    born-digital PDF — route to OCR rather than pass empty text downstream."""
    try:
        doc = fitz.open(filepath)
        if doc.page_count == 0:
            return True
        first_page_text = doc[0].get_text().strip()
        doc.close()
        return len(first_page_text) < SCANNED_TEXT_THRESHOLD
    except Exception:
        # If PyMuPDF can't even open it, treat as "needs special handling"
        # rather than crashing the whole intake scan.
        return True


def classify_file(filepath: Path) -> str:
    """Determines which parser this file needs, based on extension (and, for
    PDFs, whether it looks scanned)."""
    suffix = filepath.suffix.lower()
    if suffix == ".docx":
        return FILE_KIND_DOCX
    if suffix in (".xlsx", ".xls", ".csv"):
        return FILE_KIND_SPREADSHEET
    if suffix == ".pdf":
        return FILE_KIND_PDF_SCANNED if is_scanned_pdf(filepath) else FILE_KIND_PDF_BORN_DIGITAL
    raise ValueError(f"Unsupported file extension: {suffix}")


def scan_intake_directory(root: str | None = None) -> list[IntakeResult]:
    """Discover all supported files and classify each: doc_type + file_kind.
    Does NOT parse or store anything — that's pipeline.py's job. This is
    purely the "what do we have and what will happen to it" step, so you can
    see the classification before anything runs.
    """
    results: list[IntakeResult] = []
    for filepath in discover_source_files(root):
        results.append(
            IntakeResult(
                filepath=filepath,
                filename=filepath.name,
                doc_type=detect_doc_type(filepath),
                file_kind=classify_file(filepath),
            )
        )
    return results


_FILE_KIND_LABELS = {
    FILE_KIND_PDF_BORN_DIGITAL: "OK — born-digital PDF",
    FILE_KIND_PDF_SCANNED: "⚠️  SCANNED PDF (will be routed through OCR)",
    FILE_KIND_DOCX: "OK — DOCX",
    FILE_KIND_SPREADSHEET: "OK — spreadsheet",
}

if __name__ == "__main__":
    found = scan_intake_directory()
    if not found:
        print(f"No supported files found under {SOURCE_DOCUMENTS_DIR}. "
              f"Add .pdf or .docx files to source_documents/<subfolder>/ and re-run.")
    for r in found:
        label = _FILE_KIND_LABELS.get(r.file_kind, r.file_kind)
        print(f"{r.filename:50s}  doc_type={r.doc_type:15s}  {label}")
