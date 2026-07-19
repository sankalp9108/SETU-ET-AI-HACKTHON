"""
GraphRAG retrieval engine — Phase 4.

Combines two retrieval signals for an incoming query:
  1. Vector similarity search over Postgres/pgvector (semantic recall)
  2. A graph-side lookup in Neo4j (relationship-aware context)

Run concurrently via asyncio.to_thread (psycopg2 and the neo4j driver are
both synchronous, so real parallelism here comes from OS threads, not
asyncio's event loop directly — but the two DB round-trips still overlap
instead of running back-to-back).

IMPORTANT — current limitation, by design: entity extraction (Phase 3's
LLM step) hasn't been built yet, so Neo4j only has :Document nodes right
now — no :Equipment, :WorkOrder, etc. graph_lookup() below reflects that
honestly: it does a keyword-based Document lookup, not real relationship
traversal (MAINTAINED_BY, HAD_FAILURE, etc.). Once entity extraction is
added, extend graph_lookup() to do real Cypher traversal from matched
Equipment nodes — the merge/retrieve() logic below doesn't need to change.
"""

import asyncio
import re
from dataclasses import dataclass

from app.config import RETRIEVAL_TOP_K
from app.vectorstore.embedder import embed_texts
from app.vectorstore.store import get_connection
from app.graph.writer import get_driver

# Equipment IDs in this project follow a LETTER(S) + DIGITS pattern (e.g.
# P204, C101) per docs/source_documents_mapping.md. Used to spot likely
# equipment references in free-text queries AND in filenames.
#
# Deliberately NOT using \b word boundaries: real filenames are often
# camelCase-concatenated with no boundary at all (e.g. "PumpP204.pdf",
# "CompressorC101.pdf") — \b wouldn't fire between "p" and "P" since both
# are word characters. Instead: block a match only if immediately preceded
# by another uppercase letter or a digit (which would mean we're
# mid-token, not at a genuine new ID's start) — lowercase-to-uppercase
# transitions (the camelCase boundary) are allowed through.
EQUIPMENT_ID_PATTERN = re.compile(r"(?<![A-Z0-9])[A-Z]{1,3}\d{2,4}(?!\d)")


@dataclass
class VectorHit:
    document_id: str
    filename: str
    doc_type: str
    content: str
    similarity: float  # 0.0-1.0, higher = more similar


@dataclass
class GraphHit:
    document_id: str
    filename: str
    doc_type: str
    match_reason: str  # why this came back, e.g. "equipment_id_match: P204"


@dataclass
class RetrievalResult:
    query: str
    vector_hits: list[VectorHit]
    graph_hits: list[GraphHit]

    def combined_context(self) -> str:
        """Flattens both hit types into one context block for generation,
        each entry labeled with its source document so citations can be
        built directly from this text."""
        blocks = []
        for hit in self.vector_hits:
            blocks.append(
                f"[Source: {hit.filename} | doc_type={hit.doc_type} | "
                f"similarity={hit.similarity:.2f}]\n{hit.content}"
            )
        for hit in self.graph_hits:
            blocks.append(
                f"[Graph match: {hit.filename} | doc_type={hit.doc_type} | "
                f"reason={hit.match_reason}]"
            )
        return "\n\n---\n\n".join(blocks)

    def is_empty(self) -> bool:
        return not self.vector_hits and not self.graph_hits


def _vector_search_sync(query_embedding: list[float], top_k: int) -> list[VectorHit]:
    """Cosine similarity search over pgvector. pgvector's `<=>` operator
    returns cosine DISTANCE (0=identical, 2=opposite for normalized
    vectors), so similarity = 1 - distance."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.content, c.document_id, d.filename, d.doc_type,
                       1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s;
                """,
                (query_embedding, query_embedding, top_k),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        VectorHit(
            document_id=str(row[1]),
            filename=row[2],
            doc_type=row[3],
            content=row[0],
            similarity=float(row[4]),
        )
        for row in rows
    ]


def _graph_lookup_sync(query: str) -> list[GraphHit]:
    """Current (limited) graph-side lookup: extracts equipment-ID-shaped
    tokens from the query and matches them against Document.filename as a
    substring — a stand-in for real relationship traversal until Equipment/
    WorkOrder nodes exist. Returns [] if no equipment-like token is found,
    rather than returning irrelevant results."""
    equipment_ids = EQUIPMENT_ID_PATTERN.findall(query.upper())
    if not equipment_ids:
        return []

    driver = get_driver()
    hits: list[GraphHit] = []
    with driver.session() as session:
        for eq_id in equipment_ids:
            result = session.run(
                """
                MATCH (d:Document)
                WHERE toUpper(d.filename) CONTAINS $eq_id
                RETURN d.id AS id, d.filename AS filename, d.doc_type AS doc_type
                """,
                eq_id=eq_id,
            )
            for record in result:
                hits.append(
                    GraphHit(
                        document_id=record["id"],
                        filename=record["filename"],
                        doc_type=record["doc_type"],
                        match_reason=f"equipment_id_match: {eq_id}",
                    )
                )
    return hits


async def retrieve(query: str, top_k: int = RETRIEVAL_TOP_K) -> RetrievalResult:
    """Runs vector search and graph lookup concurrently, merges into one
    RetrievalResult. This is the single entry point agents call — Self-RAG
    grading (retrieval/self_rag.py) happens as a separate step after this."""
    query_embedding = embed_texts([query])[0]

    vector_task = asyncio.to_thread(_vector_search_sync, query_embedding, top_k)
    graph_task = asyncio.to_thread(_graph_lookup_sync, query)

    vector_hits, graph_hits = await asyncio.gather(vector_task, graph_task)

    return RetrievalResult(query=query, vector_hits=vector_hits, graph_hits=graph_hits)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print('Usage: python -m app.retrieval.graphrag "your question here"')
        sys.exit(1)

    query_text = " ".join(sys.argv[1:])
    result = asyncio.run(retrieve(query_text))

    print(f"Query: {query_text}")
    print(f"Vector hits: {len(result.vector_hits)}, Graph hits: {len(result.graph_hits)}\n")
    for hit in result.vector_hits:
        print(f"  [vector] {hit.filename} (sim={hit.similarity:.3f}): {hit.content[:100]}...")
    for hit in result.graph_hits:
        print(f"  [graph]  {hit.filename} ({hit.match_reason})")

    if result.is_empty():
        print("\nNo results — either the corpus is empty or nothing matched.")
