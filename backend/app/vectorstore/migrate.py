"""
One-time Postgres migration: applies migrations/postgres/001_init.sql.

Run this once after `docker-compose up` brings Postgres up:

    python -m app.vectorstore.migrate

Safe to re-run — every statement uses IF NOT EXISTS.

The VECTOR(N) dimension in the SQL file is a placeholder (384, matching the
'local' provider default) — this script substitutes it with whatever
EMBEDDING_DIM is actually set to in .env before executing, so a fresh
install always gets the right dimension automatically. No manual editing
of the .sql file needed when switching providers on a FRESH database.

IMPORTANT: this only helps fresh installs. If you already ran this against
an existing database at a different dimension (e.g. you started with 'local'
384-dim and are now switching to 'google' 768-dim), the existing table
already has the old dimension baked in — re-running this script won't alter
it (CREATE TABLE IF NOT EXISTS is a no-op if the table exists). Use
migrations/postgres/002_switch_to_google_embeddings.sql for that transition
instead.
"""

import os
import re
import psycopg2

from app.config import POSTGRES_URL, EMBEDDING_DIM

MIGRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "migrations",
    "postgres",
    "001_init.sql",
)


def run_migration() -> None:
    with open(MIGRATION_FILE, "r") as f:
        sql = f.read()

    # Substitute the placeholder VECTOR(384) with the actual configured
    # dimension, so this always matches .env regardless of which provider
    # you've chosen — no manual .sql editing needed for a fresh install.
    sql = re.sub(r"VECTOR\(\d+\)", f"VECTOR({EMBEDDING_DIM})", sql)

    conn = psycopg2.connect(POSTGRES_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print(f"Migration applied successfully against {POSTGRES_URL.split('@')[-1]}")
        print(f"chunks.embedding created as VECTOR({EMBEDDING_DIM})")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name;"
            )
            tables = [row[0] for row in cur.fetchall()]
            print("Tables now present:", tables)
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
