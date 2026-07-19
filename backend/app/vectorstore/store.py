"""
Postgres write layer — Phase 3.

Inserts into the `documents` and `chunks` tables created by
migrations/postgres/001_init.sql. No entity extraction happens here — just
storing the parsed/chunked/embedded text so it's queryable by Phase 4
(retrieval).
"""

import psycopg2
from psycopg2.extras import execute_values

from app.config import POSTGRES_URL


def get_connection():
    return psycopg2.connect(POSTGRES_URL)


def insert_document(conn, doc_id: str, filename: str, doc_type: str, equipment_id: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (id, filename, doc_type, equipment_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
            """,
            (doc_id, filename, doc_type, equipment_id),
        )
    conn.commit()


def get_documents_by_doc_types(conn, doc_types: list[str]) -> list[dict]:
    """Returns {id, filename, doc_type} for every ingested document matching
    any of the given doc_types. Used by the Compliance agent to split the
    corpus into a 'regulatory subset' vs. documents that should be checked
    against it — works directly off doc_type, which is populated at
    ingestion time (Phase 3), no entity extraction required."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, filename, doc_type FROM documents WHERE doc_type = ANY(%s) "
            "ORDER BY filename;",
            (doc_types,),
        )
        rows = cur.fetchall()
    return [{"id": str(r[0]), "filename": r[1], "doc_type": r[2]} for r in rows]


def get_document_full_text(conn, document_id: str) -> str:
    """Reassembles a document's full text from its chunks, in chunk_index
    order. Used when an agent needs the whole document, not just top-k
    similarity-matched pieces (e.g. Compliance checking one procedure
    against regulatory references in full, not a fragment of it)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content FROM chunks WHERE document_id = %s ORDER BY chunk_index;",
            (document_id,),
        )
        rows = cur.fetchall()
    return "\n".join(r[0] for r in rows)


def vector_search_by_doc_type(conn, query_embedding: list[float], doc_type: str, top_k: int) -> list[dict]:
    """Cosine similarity search restricted to a single doc_type — used by the
    Lessons-Learned agent to compare a new incident description only
    against past incident documents, not the whole corpus (a similar-sounding
    SOP or policy chunk isn't a 'similar past incident')."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.content, c.document_id, d.filename,
                   1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.doc_type = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s;
            """,
            (query_embedding, doc_type, query_embedding, top_k),
        )
        rows = cur.fetchall()
    return [
        {"content": r[0], "document_id": str(r[1]), "filename": r[2], "similarity": float(r[3])}
        for r in rows
    ]


def insert_chunks(conn, doc_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
            f"counts don't match — something upstream is out of sync."
        )
    if not chunks:
        return

    rows = [
        (doc_id, content, embedding, idx)
        for idx, (content, embedding) in enumerate(zip(chunks, embeddings))
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO chunks (document_id, content, embedding, chunk_index)
            VALUES %s
            ON CONFLICT (document_id, chunk_index) DO NOTHING;
            """,
            rows,
        )
    conn.commit()
