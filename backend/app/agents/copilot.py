"""
Copilot agent — Phase 5.

Pipeline: question -> graphrag.retrieve() -> self_rag.grade_retrieval()
  -> if insufficient_evidence: return an explicit "I don't know" response
  -> else: generate an answer from ONLY the relevant graded context

Citations and confidence are computed by CODE, not trusted from the LLM's
own response — the model is asked to answer using only the given context,
but the citations list attached to the API response is built directly from
which graded chunks were actually marked relevant. This is the enforcement
mechanism from the build plan ("citations are not an add-on, they are
enforced at the retrieval layer") — the LLM can't fabricate a citation to a
document that wasn't actually retrieved and graded relevant.
"""

from app.config import LLM_MODEL_REASONING
from app.llm_client import generate_text
from app.retrieval.graphrag import retrieve
from app.retrieval.self_rag import grade_retrieval, GradedRetrieval
from app.models.schemas import CopilotQueryResponse

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I don't have enough information in the ingested documents to answer that "
    "confidently. Try rephrasing, or check if the relevant document has been "
    "ingested yet."
)


def _build_citations(graded: GradedRetrieval) -> list[str]:
    """Unique filenames from chunks that actually passed grading, plus any
    graph hits — in the order they were found. Deduplicated because a
    document can contribute multiple relevant chunks."""
    seen = []
    for chunk in graded.graded_chunks:
        if chunk.relevant and chunk.filename not in seen:
            seen.append(chunk.filename)
    for hit in graded.graph_hits:
        if hit.filename not in seen:
            seen.append(hit.filename)
    return seen


def _compute_confidence(graded: GradedRetrieval) -> float:
    """Average similarity score of the chunks that passed grading — not an
    LLM self-report. Graph hits (exact equipment-ID matches) don't have a
    similarity score, so they don't factor into this average; their presence
    already contributes to citations and to clearing insufficient_evidence."""
    relevant_scores = [c.similarity for c in graded.graded_chunks if c.relevant]
    if not relevant_scores:
        return 0.0
    return round(sum(relevant_scores) / len(relevant_scores), 2)


def _build_generation_prompt(question: str, context: str) -> str:
    return f"""You are a plant maintenance and safety assistant. Answer the
question using ONLY the context below — do not use outside knowledge, and do
not guess. If the context doesn't actually contain the answer, say so
explicitly rather than filling gaps.

Context:
{context}

Question: {question}

Give a clear, direct answer grounded only in the context above."""


async def answer_question(question: str) -> CopilotQueryResponse:
    """Main Copilot entry point. Async because retrieval runs vector search
    and graph lookup concurrently (see graphrag.retrieve)."""
    retrieval = await retrieve(question)
    graded = grade_retrieval(retrieval)

    if graded.insufficient_evidence:
        return CopilotQueryResponse(
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            citations=[],
            confidence=0.0,
            insufficient_evidence=True,
        )

    context = graded.relevant_context()
    prompt = _build_generation_prompt(question, context)
    answer_text = generate_text(prompt, model=LLM_MODEL_REASONING, max_tokens=500)

    return CopilotQueryResponse(
        answer=answer_text.strip(),
        citations=_build_citations(graded),
        confidence=_compute_confidence(graded),
        insufficient_evidence=False,
    )


if __name__ == "__main__":
    import asyncio
    import sys

    if len(sys.argv) < 2:
        print('Usage: python -m app.agents.copilot "your question here"')
        sys.exit(1)

    question_text = " ".join(sys.argv[1:])
    result = asyncio.run(answer_question(question_text))

    print(f"Question: {question_text}\n")
    print(f"Answer: {result.answer}\n")
    print(f"Citations: {result.citations}")
    print(f"Confidence: {result.confidence}")
    print(f"Insufficient evidence: {result.insufficient_evidence}")
