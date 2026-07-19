"""
Lessons-Learned agent — Phase 8.

Pipeline: new incident description -> embed it -> vector similarity search
restricted to doc_type='incident' documents (so a similar-sounding SOP or
policy chunk never counts as a "similar past incident") -> filter by
LESSONS_LEARNED_SIMILARITY_THRESHOLD -> for surviving matches, add a second
signal: does the matched document's filename share an equipment-ID-shaped
token with the query text? (same regex approach as graphrag.py's graph
lookup — consistent with that documented limitation until entity extraction
adds real Equipment nodes to check shared equipment type/failure mode
against instead of just filename text).

Works the moment you ingest even one incident report into
source_documents/incidents/ — doesn't need entity extraction, same as
Compliance. Right now, with zero incident documents ingested, this
correctly returns insufficient_data=True.
"""

from app.config import LESSONS_LEARNED_SIMILARITY_THRESHOLD, RETRIEVAL_TOP_K
from app.vectorstore.embedder import embed_texts
from app.vectorstore.store import get_connection, vector_search_by_doc_type
from app.retrieval.graphrag import EQUIPMENT_ID_PATTERN
from app.models.schemas import LessonsLearnedAlert, LessonsLearnedReport

INCIDENT_DOC_TYPE = "incident"


def _shared_equipment_ids(query: str, filename: str) -> list[str]:
    """Returns equipment-ID-shaped tokens present in BOTH the query text and
    the matched document's filename — a lightweight stand-in for a real
    'same equipment' graph check until Equipment nodes exist.

    IMPORTANT: extraction runs on the ORIGINAL case of each string, not
    uppercased first — filenames are often camelCase-concatenated (e.g.
    "CompressorC101.pdf") and uppercasing before extraction would destroy
    the lowercase-to-uppercase transition the regex relies on to find the
    ID's start. Only the extracted tokens themselves are uppercased
    afterward, for a case-insensitive set comparison."""
    query_ids = {m.upper() for m in EQUIPMENT_ID_PATTERN.findall(query)}
    filename_ids = {m.upper() for m in EQUIPMENT_ID_PATTERN.findall(filename)}
    return sorted(query_ids & filename_ids)


def _build_note(similarity: float, shared_ids: list[str]) -> str:
    base = f"Similar past incident (similarity {similarity:.2f})"
    if shared_ids:
        base += f" — also references the same equipment ({', '.join(shared_ids)})"
    return base


def check_lessons_learned(incident_description: str, top_k: int = RETRIEVAL_TOP_K) -> LessonsLearnedReport:
    """Main entry point. Synchronous (single data source: pgvector), unlike
    Copilot which parallelizes vector + graph retrieval."""
    query_embedding = embed_texts([incident_description])[0]

    conn = get_connection()
    try:
        hits = vector_search_by_doc_type(conn, query_embedding, INCIDENT_DOC_TYPE, top_k)
    finally:
        conn.close()

    if not hits:
        return LessonsLearnedReport(
            query=incident_description,
            alerts=[],
            insufficient_data=True,
            note="No past incident documents have been ingested yet. Add incident "
                 "reports to source_documents/incidents/ and re-run the ingestion "
                 "pipeline before checking for similar past incidents.",
        )

    alerts = []
    for hit in hits:
        if hit["similarity"] < LESSONS_LEARNED_SIMILARITY_THRESHOLD:
            continue
        shared_ids = _shared_equipment_ids(incident_description, hit["filename"])
        alerts.append(
            LessonsLearnedAlert(
                filename=hit["filename"],
                similarity=hit["similarity"],
                excerpt=hit["content"][:300],
                shared_equipment_ids=shared_ids,
                note=_build_note(hit["similarity"], shared_ids),
            )
        )

    return LessonsLearnedReport(
        query=incident_description,
        alerts=alerts,
        insufficient_data=False,
        note="" if alerts else (
            f"Past incident documents exist, but none scored above the "
            f"similarity threshold ({LESSONS_LEARNED_SIMILARITY_THRESHOLD}) — "
            f"this may genuinely be a novel type of incident."
        ),
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print('Usage: python -m app.agents.lessons_learned "description of the new incident"')
        sys.exit(1)

    description = " ".join(sys.argv[1:])
    report = check_lessons_learned(description)

    print(f"Query: {report.query}")
    print(f"Insufficient data: {report.insufficient_data}")
    if report.note:
        print(f"Note: {report.note}")
    print(f"\nAlerts: {len(report.alerts)}")
    for alert in report.alerts:
        print(f"  {alert.filename} (similarity={alert.similarity:.2f})")
        print(f"    {alert.note}")
        print(f"    Excerpt: {alert.excerpt}")
