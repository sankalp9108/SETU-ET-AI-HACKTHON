"""
Ingestion pipeline orchestrator — Phase 3 (PDF + OCR + DOCX + Spreadsheet slice).

Current scope, deliberately:
  intake (file discovery + classification)
    → pdf_parser (born-digital PDF) OR ocr_parser (scanned PDF)
      OR docx_parser (DOCX) OR spreadsheet_parser (xlsx/xls/csv)
    → chunker → embedder (local, no API key needed) → store (Postgres + Neo4j)

NOT in scope yet (needs an LLM key):
  - LLM entity extraction (Equipment/WorkOrder/Procedure/etc. nodes)
  - Relationship writing (MAINTAINED_BY, HAD_FAILURE, etc.)

This is the full Phase 3 ingestion scope from the build plan, minus entity
extraction — every document TYPE the plan calls for can now be parsed,
chunked, embedded, and stored end to end.

Run with:
    python -m app.ingestion.pipeline

source_documents/ is currently empty by design — drop files into the
correct subfolder (see docs/source_documents_mapping.md) and re-run any time.
"""

import uuid

from app.ingestion.intake import (
    scan_intake_directory,
    FILE_KIND_PDF_BORN_DIGITAL,
    FILE_KIND_PDF_SCANNED,
    FILE_KIND_DOCX,
    FILE_KIND_SPREADSHEET,
)
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.ocr_parser import parse_scanned_pdf
from app.ingestion.docx_parser import parse_docx
from app.ingestion.spreadsheet_parser import parse_spreadsheet
from app.ingestion.chunker import chunk_text
from app.vectorstore.embedder import embed_texts
from app.vectorstore.store import get_connection, insert_document, insert_chunks
from app.graph.writer import write_document_node

_PARSERS = {
    FILE_KIND_PDF_BORN_DIGITAL: parse_pdf,
    FILE_KIND_PDF_SCANNED: parse_scanned_pdf,
    FILE_KIND_DOCX: parse_docx,
    FILE_KIND_SPREADSHEET: parse_spreadsheet,
}


def ingest_one_file(filepath, doc_type: str, file_kind: str) -> str:
    """Runs one file through the full parse→chunk→embed→store flow, using
    whichever parser matches its file_kind. Returns the generated doc_id
    (same UUID written to both Postgres and Neo4j — see
    docs/data_model_conventions.md)."""
    doc_id = str(uuid.uuid4())
    filename = filepath.name

    parser_fn = _PARSERS[file_kind]
    parsed = parser_fn(filepath)
    chunks = chunk_text(parsed.full_text)

    if not chunks:
        print(f"  ⚠️  {filename}: no text chunks produced, skipping store step")
        return doc_id

    embeddings = embed_texts(chunks)

    conn = get_connection()
    try:
        insert_document(conn, doc_id=doc_id, filename=filename, doc_type=doc_type)
        insert_chunks(conn, doc_id=doc_id, chunks=chunks, embeddings=embeddings)
    finally:
        conn.close()

    write_document_node(doc_id=doc_id, filename=filename, doc_type=doc_type)

    extractor = parsed.extractor_used
    print(f"  ✅ {filename}: {len(chunks)} chunks stored via {extractor} (doc_id={doc_id})")
    return doc_id


def run_pipeline() -> None:
    results = scan_intake_directory()

    if not results:
        print("No supported files found under source_documents/. Add .pdf/.docx "
              "files to the correct subfolder (see docs/source_documents_mapping.md) "
              "and re-run.")
        return

    processed, skipped = 0, 0
    for r in results:
        if r.doc_type == "unknown":
            print(f"  ⚠️  {r.filename}: in an unrecognized folder, doc_type='unknown' "
                  f"— still ingesting, but check source_documents_mapping.md")

        try:
            ingest_one_file(r.filepath, r.doc_type, r.file_kind)
            processed += 1
        except ValueError as e:
            print(f"  ❌ {r.filename}: {e}")
            skipped += 1

    print(f"\nDone. Processed: {processed}, Skipped: {skipped}")


if __name__ == "__main__":
    run_pipeline()
