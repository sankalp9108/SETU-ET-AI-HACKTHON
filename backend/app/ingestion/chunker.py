"""
Text chunking — splits parsed document text into overlapping chunks before
embedding. Word-count based (not a real tokenizer) — good enough for the MVP,
matches the ~500 token / ~50 token overlap defaults from app/config.py
closely enough since English averages ~0.75 words per token.
"""

from app.config import CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS


def chunk_text(
    text: str,
    chunk_size_tokens: int = CHUNK_SIZE_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """Splits text into overlapping chunks by (approximate) word count.
    Returns a list of chunk strings, in order. Empty/whitespace-only input
    returns an empty list rather than a list with one blank chunk."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    step = max(chunk_size_tokens - overlap_tokens, 1)  # guard against overlap >= size

    while start < len(words):
        end = start + chunk_size_tokens
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += step

    return chunks


if __name__ == "__main__":
    sample = "word " * 1200
    result = chunk_text(sample)
    print(f"Produced {len(result)} chunks from 1200 words "
          f"(chunk_size={CHUNK_SIZE_TOKENS}, overlap={CHUNK_OVERLAP_TOKENS})")
