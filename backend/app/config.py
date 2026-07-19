"""
Central configuration for the SETU backend MVP.

Everything that varies by environment (DB URLs, API keys, model names) is loaded
from environment variables here, and nowhere else. Every other module should
import from this file rather than calling os.getenv() directly, so there is
exactly one source of truth for config.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


# --- Neo4j ---
NEO4J_URI = _require("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = _require("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = _require("NEO4J_PASSWORD", "setu_dev_password")

# --- Postgres / pgvector ---
POSTGRES_URL = _require(
    "POSTGRES_URL", "postgresql://setu:setu_dev_password@localhost:5432/setu"
)

# --- LLM providers ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

LLM_MODEL_REASONING = _require("LLM_MODEL_REASONING", "claude-sonnet-4-6")
LLM_MODEL_EXTRACTION = _require(
    "LLM_MODEL_EXTRACTION", "claude-haiku-4-5-20251001"
)


def has_llm_key() -> bool:
    """True if any LLM provider is configured. Used by modules (self_rag.py,
    agents/*) that need to know whether to use real LLM calls or fall back
    to a non-LLM heuristic — checking all three keys in one place means
    adding a 4th provider later only requires a change here."""
    return bool(GEMINI_API_KEY or ANTHROPIC_API_KEY or OPENAI_API_KEY)

# --- Embeddings: LOCKED CHOICE. Do not change EMBEDDING_DIM after the first
# ingestion run — it must match the `chunks.embedding VECTOR(N)` column in
# Postgres exactly, or every insert/query against that table breaks. ---
EMBEDDING_PROVIDER = _require("EMBEDDING_PROVIDER", "local")  # "local" | "openai" | "google"
EMBEDDING_DIM = int(_require("EMBEDDING_DIM", "384"))

# Google's text-embedding-004 (768-dim) — used when EMBEDDING_PROVIDER=google.
EMBEDDING_MODEL_GOOGLE = os.getenv("EMBEDDING_MODEL_GOOGLE", "text-embedding-004")

_VALID_DIMS = {"local": 384, "openai": 1536, "google": 768}
if EMBEDDING_DIM != _VALID_DIMS.get(EMBEDDING_PROVIDER):
    raise RuntimeError(
        f"EMBEDDING_DIM={EMBEDDING_DIM} does not match the expected dimension "
        f"for EMBEDDING_PROVIDER={EMBEDDING_PROVIDER} "
        f"(expected {_VALID_DIMS.get(EMBEDDING_PROVIDER)}). "
        f"Fix .env before running ingestion."
    )

# --- App ---
APP_ENV = os.getenv("APP_ENV", "dev")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# --- Ingestion tuning defaults ---
CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50
RETRIEVAL_TOP_K = 5
SELF_RAG_RELEVANCE_THRESHOLD = 0.6  # below this, treat as "insufficient evidence"
LESSONS_LEARNED_SIMILARITY_THRESHOLD = 0.65  # below this, not a genuine "similar past incident"

# --- Poppler (required by pdf2image for OCR rasterization) ---
# On Linux/Mac, poppler is usually already on PATH after installing via
# apt/brew, so this can stay blank. On Windows, pdf2image can't find
# pdftoppm/pdfinfo automatically — download poppler for Windows, extract it,
# and point this at the bin/ folder, e.g.:
#   POPPLER_PATH=C:\poppler\Library\bin
POPPLER_PATH = os.getenv("POPPLER_PATH") or None

# --- Tesseract executable (required by pytesseract) ---
# Same story as poppler above — Linux/Mac usually don't need this set after
# installing tesseract via apt/brew. On Windows, after installing Tesseract-OCR
# (https://github.com/UB-Mannheim/tesseract/wiki), point this at tesseract.exe:
#   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or None

# --- Source documents ---
SOURCE_DOCUMENTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "source_documents"
)
