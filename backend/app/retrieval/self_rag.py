"""
Self-RAG grading layer — Phase 4.

Grades retrieved chunks for relevance BEFORE they're allowed to reach
generation. If nothing passes the bar, the caller should return an explicit
"insufficient evidence" response rather than answering on weak grounding
(build plan, Section 06, Stage 06).

Two grading modes, chosen automatically — no code changes needed when you
add an API key later:

  - LLM mode (if ANTHROPIC_API_KEY is set in .env): asks the reasoning model
    to judge each chunk's relevance to the query directly. More accurate,
    catches cases where a chunk is topically similar but doesn't actually
    answer the question.
  - Heuristic fallback (no API key): uses the vector similarity score from
    graphrag.py against SELF_RAG_RELEVANCE_THRESHOLD. Cruder, but fully
    functional right now with zero API cost — good enough to prove the
    "insufficient evidence" path works before an LLM is wired in.
"""

import json
from dataclasses import dataclass

from app.config import LLM_MODEL_REASONING, SELF_RAG_RELEVANCE_THRESHOLD, has_llm_key
from app.llm_client import generate_text
from app.retrieval.graphrag import VectorHit, GraphHit, RetrievalResult


@dataclass
class GradedChunk:
    filename: str
    doc_type: str
    content: str
    similarity: float
    relevant: bool
    grading_method: str  # "llm" | "heuristic"
    reason: str = ""


@dataclass
class GradedRetrieval:
    query: str
    graded_chunks: list[GradedChunk]
    graph_hits: list[GraphHit]
    insufficient_evidence: bool

    def relevant_context(self) -> str:
        """Only the chunks that passed grading, formatted for generation."""
        blocks = [
            f"[Source: {c.filename} | doc_type={c.doc_type}]\n{c.content}"
            for c in self.graded_chunks if c.relevant
        ]
        for hit in self.graph_hits:
            blocks.append(f"[Graph match: {hit.filename} | reason={hit.match_reason}]")
        return "\n\n---\n\n".join(blocks)


def _grade_heuristic(query: str, hits: list[VectorHit]) -> list[GradedChunk]:
    """No API key available — falls back to the embedding similarity score
    already computed during vector search. Simple, transparent, and testable
    without spending any LLM tokens."""
    return [
        GradedChunk(
            filename=h.filename,
            doc_type=h.doc_type,
            content=h.content,
            similarity=h.similarity,
            relevant=h.similarity >= SELF_RAG_RELEVANCE_THRESHOLD,
            grading_method="heuristic",
            reason=f"similarity {h.similarity:.2f} vs threshold {SELF_RAG_RELEVANCE_THRESHOLD}",
        )
        for h in hits
    ]


def _grade_with_llm(query: str, hits: list[VectorHit]) -> list[GradedChunk]:
    """Asks the reasoning LLM (whichever provider is configured — see
    app/llm_client.py) to judge each chunk's relevance in one batched call
    (cheaper and faster than one call per chunk). Falls back to the
    heuristic for any chunk the LLM response doesn't cover, rather than
    crashing on a malformed response."""
    chunks_block = "\n\n".join(
        f"[Chunk {i}] (from {h.filename})\n{h.content}" for i, h in enumerate(hits)
    )
    prompt = f"""You are grading retrieved document chunks for relevance to a user's question.

Question: {query}

Chunks:
{chunks_block}

For each chunk, decide if it's genuinely relevant and useful for answering the question
(not just topically similar). Respond with ONLY a JSON array, no other text, in this exact
shape:
[{{"chunk_index": 0, "relevant": true, "reason": "short reason"}}, ...]
"""

    raw_text = generate_text(prompt, model=LLM_MODEL_REASONING, max_tokens=1000).strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        grades = {g["chunk_index"]: g for g in json.loads(raw_text)}
    except (json.JSONDecodeError, KeyError):
        # LLM didn't return parseable JSON — fail safe to the heuristic
        # rather than crashing the whole request.
        return _grade_heuristic(query, hits)

    graded_chunks = []
    for i, h in enumerate(hits):
        grade = grades.get(i)
        if grade is None:
            # LLM skipped this chunk in its response — fall back to
            # heuristic for just this one rather than dropping it silently.
            graded_chunks.append(_grade_heuristic(query, [h])[0])
            continue
        graded_chunks.append(
            GradedChunk(
                filename=h.filename,
                doc_type=h.doc_type,
                content=h.content,
                similarity=h.similarity,
                relevant=bool(grade.get("relevant", False)),
                grading_method="llm",
                reason=grade.get("reason", ""),
            )
        )
    return graded_chunks


def grade_retrieval(retrieval: RetrievalResult) -> GradedRetrieval:
    """Main entry point. Grades every vector hit in a RetrievalResult and
    determines whether there's enough relevant evidence to answer at all.
    Graph hits are passed through ungraded for now — they're already a
    precise equipment-ID match, not a fuzzy similarity result, so there's
    no ambiguous "relevant?" judgment to make on them yet."""
    if not retrieval.vector_hits:
        graded_chunks = []
    elif has_llm_key():
        graded_chunks = _grade_with_llm(retrieval.query, retrieval.vector_hits)
    else:
        graded_chunks = _grade_heuristic(retrieval.query, retrieval.vector_hits)

    any_relevant = any(c.relevant for c in graded_chunks) or bool(retrieval.graph_hits)

    return GradedRetrieval(
        query=retrieval.query,
        graded_chunks=graded_chunks,
        graph_hits=retrieval.graph_hits,
        insufficient_evidence=not any_relevant,
    )


if __name__ == "__main__":
    import asyncio
    import sys

    from app.retrieval.graphrag import retrieve

    if len(sys.argv) < 2:
        print('Usage: python -m app.retrieval.self_rag "your question here"')
        sys.exit(1)

    query_text = " ".join(sys.argv[1:])
    retrieval_result = asyncio.run(retrieve(query_text))
    graded = grade_retrieval(retrieval_result)

    mode = "LLM" if has_llm_key() else "heuristic (no API key set)"
    print(f"Query: {query_text}")
    print(f"Grading mode: {mode}\n")

    for c in graded.graded_chunks:
        flag = "✅ RELEVANT" if c.relevant else "❌ not relevant"
        print(f"  {flag}  {c.filename}  ({c.reason})")

    print(f"\nInsufficient evidence: {graded.insufficient_evidence}")
    if not graded.insufficient_evidence:
        print(f"\n--- Context that would be passed to generation ---\n{graded.relevant_context()[:500]}")
