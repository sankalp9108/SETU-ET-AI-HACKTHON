"""
Embedding wrapper — Phase 3/4.

Three providers supported, chosen by EMBEDDING_PROVIDER in .env:
  - "local"  : bge-small-en via sentence-transformers (384-dim, no API key)
  - "google" : Gemini's text-embedding-004 via google-genai (768-dim)
  - "openai" : stubbed, not implemented yet (1536-dim)

Switching providers requires EMBEDDING_DIM in .env to match (see
docs/data_model_conventions.md) AND the Postgres chunks.embedding column to
be recreated at the new dimension — this isn't a drop-in runtime swap, it's
a schema change. See migrations/postgres/002_switch_to_google_embeddings.sql
if you already had a table created at the old dimension.

Local model is loaded lazily (only on first call) so importing this module
doesn't pay the model-load cost if it's never actually used.
"""

from app.config import EMBEDDING_PROVIDER, EMBEDDING_DIM, EMBEDDING_MODEL_GOOGLE, GEMINI_API_KEY

_model = None


def _get_local_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _model


def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _get_local_model()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def _embed_google(texts: list[str]) -> list[list[float]]:
    """Google's embed_content accepts a batch of strings in one call.
    Uses RETRIEVAL_DOCUMENT as the task type for ingestion-time embedding —
    if you later add a separate query-time embedding call for retrieval,
    Google recommends RETRIEVAL_QUERY there instead for best results (the
    two task types are optimized asymmetrically for document vs. query
    text), but a single task type for both is fine for the MVP."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    result = client.models.embed_content(
        model=EMBEDDING_MODEL_GOOGLE,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return [embedding.values for embedding in result.embeddings]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeds a list of text chunks, returning one vector per input in the
    same order. Batches internally for efficiency."""
    if not texts:
        return []

    if EMBEDDING_PROVIDER == "local":
        vectors_list = _embed_local(texts)
    elif EMBEDDING_PROVIDER == "google":
        vectors_list = _embed_google(texts)
    elif EMBEDDING_PROVIDER == "openai":
        raise NotImplementedError(
            "EMBEDDING_PROVIDER=openai is configured but not implemented yet. "
            "Switching providers also requires updating the Postgres "
            "VECTOR(N) column dimension — see docs/data_model_conventions.md "
            "before implementing this branch."
        )
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")

    for v in vectors_list:
        if len(v) != EMBEDDING_DIM:
            raise RuntimeError(
                f"Embedding model returned {len(v)}-dim vectors but "
                f"EMBEDDING_DIM={EMBEDDING_DIM}. Config and model are out of "
                f"sync — fix before writing to Postgres."
            )

    return vectors_list


if __name__ == "__main__":
    test_vectors = embed_texts(["hello world", "a second test sentence"])
    print(f"Provider: {EMBEDDING_PROVIDER}")
    print(f"Produced {len(test_vectors)} vectors, dim={len(test_vectors[0])}")
