"""
Neo4j write layer — Phase 3 (PDF-only slice).

Only writes a minimal :Document node per ingested file right now — filename,
doc_type, ingested_at. NO entity extraction (Equipment/WorkOrder/Procedure/
etc. nodes) happens here yet — that requires an LLM call, which is a later
step once an API key is wired in. This just establishes the Document node
so retrieval can join a Postgres chunk back to something in the graph.

Uses MERGE, never CREATE, per the convention in docs/data_model_conventions.md
— re-ingesting the same file (same doc_id) won't create a duplicate node.
"""

from neo4j import GraphDatabase

from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def write_document_node(doc_id: str, filename: str, doc_type: str) -> None:
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (d:Document {id: $doc_id})
            ON CREATE SET d.filename = $filename,
                          d.doc_type = $doc_type,
                          d.ingested_at = datetime()
            ON MATCH SET  d.filename = $filename,
                          d.doc_type = $doc_type
            """,
            doc_id=doc_id,
            filename=filename,
            doc_type=doc_type,
        )
