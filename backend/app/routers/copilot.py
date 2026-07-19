"""
Copilot router — Phase 5.

POST /copilot/query — the first real API endpoint. Thin wrapper around
agents/copilot.py; all the actual logic (retrieval, grading, generation,
citation enforcement) lives there, not here.
"""

from fastapi import APIRouter, HTTPException

from app.agents.copilot import answer_question
from app.models.schemas import CopilotQueryRequest, CopilotQueryResponse

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/query", response_model=CopilotQueryResponse)
async def query_copilot(request: CopilotQueryRequest) -> CopilotQueryResponse:
    try:
        return await answer_question(request.question)
    except Exception as e:
        # Catches everything: no LLM key configured, Postgres/Neo4j
        # connection failures, malformed LLM responses that slipped past
        # internal fallbacks, etc. A clean 503 with the real error message
        # beats a raw Python traceback reaching the frontend.
        raise HTTPException(status_code=503, detail=str(e))
