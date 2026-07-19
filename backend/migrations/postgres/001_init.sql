-- SETU — Postgres + pgvector schema (migration 001)
-- Run against the `setu` database once docker-compose brings Postgres up:
--   psql "$POSTGRES_URL" -f migrations/postgres/001_init.sql
--
-- IMPORTANT: the VECTOR(N) dimension below MUST match EMBEDDING_DIM in .env /
-- app/config.py exactly. Changing the embedding model after this table is
-- created (e.g. switching bge-small-en's 384-dim to OpenAI's 1536-dim)
-- breaks every existing row and requires a full re-embed + table rebuild.
-- Lock this choice before running this migration, not after.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- provides gen_random_uuid()

-- One row per ingested source file. `id` here MUST equal the `Document.id`
-- property on the corresponding Neo4j node — same UUID string in both
-- stores. This is the join key GraphRAG uses to merge a vector hit with its
-- graph node in a single lookup (see app/retrieval/graphrag.py).
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT NOT NULL,
  doc_type TEXT NOT NULL,        -- 'work_order' | 'procedure' | 'incident' | 'inspection' | 'drawing' | 'email' | 'policy' | 'oem_manual'
  equipment_id TEXT,             -- soft ref to Neo4j Equipment.id, not FK-enforced across DBs
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chunked text + embeddings for vector similarity search.
-- Dimension is set to 384 (bge-small-en) to match the default
-- EMBEDDING_PROVIDER=local in .env.example. Change both together if you
-- switch to EMBEDDING_PROVIDER=openai (1536-dim) BEFORE first ingestion run.
CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  embedding VECTOR(384),
  chunk_index INT NOT NULL,
  UNIQUE (document_id, chunk_index)
);

-- ivfflat index for approximate nearest-neighbor cosine search.
-- `lists = 100` is a reasonable default for a small demo corpus; ivfflat
-- needs at least a few thousand rows to be meaningfully faster than a full
-- scan, but the index is harmless (and correct) at small scale too.
CREATE INDEX IF NOT EXISTS chunks_embedding_cosine_idx
  ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Helpful lookup indexes for the retrieval layer and agent queries.
CREATE INDEX IF NOT EXISTS documents_doc_type_idx ON documents (doc_type);
CREATE INDEX IF NOT EXISTS documents_equipment_id_idx ON documents (equipment_id);
CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks (document_id);
