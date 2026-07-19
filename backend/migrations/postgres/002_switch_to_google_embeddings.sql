-- SETU — switch an EXISTING chunks table from local (384-dim) to Google
-- text-embedding-004 (768-dim) embeddings.
--
-- Only needed if you already ran migrations/postgres/001_init.sql before
-- switching EMBEDDING_PROVIDER to "google" in .env. A fresh install doesn't
-- need this — app/vectorstore/migrate.py now creates the column at the
-- right dimension automatically based on .env.
--
-- This clears existing chunk rows. That's expected and safe: embeddings
-- from a different model/dimension are meaningless once you switch
-- providers anyway (you'd need to re-embed everything regardless) — this
-- migration just makes that explicit instead of leaving stale, useless
-- 384-dim vectors sitting in a column that's about to reject them.
--
-- Run with: psql "$POSTGRES_URL" -f migrations/postgres/002_switch_to_google_embeddings.sql

DROP INDEX IF EXISTS chunks_embedding_cosine_idx;
TRUNCATE TABLE chunks;
ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768);
CREATE INDEX chunks_embedding_cosine_idx
  ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- After running this: re-run `python -m app.ingestion.pipeline` to re-embed
-- and re-store every document in source_documents/ using Google embeddings.
