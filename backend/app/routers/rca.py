"""
RCA router — Phase 6.

POST /rca/query — thin wrapper around agents/rca.py, same pattern as
routers/copilot.py.
"""

from fastapi import APIRouter, HTTPException

from app.agents.rca import get_rca_report
from app.models.schemas import RCAQueryRequest, RCAQueryResponse

router = APIRouter(prefix="/rca", tags=["rca"])


@router.post("/query", response_model=RCAQueryResponse)
def query_rca(request: RCAQueryRequest) -> RCAQueryResponse:
    try:
        return get_rca_report(request.equipment_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
