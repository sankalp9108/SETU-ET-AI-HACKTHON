"""
Compliance router — Phase 7.

GET /compliance/gaps — no request body needed; runs a check across the
whole ingested corpus (contrast with /copilot/query and /rca/query, which
take a specific question/equipment_id).
"""

from fastapi import APIRouter, HTTPException

from app.agents.compliance import run_compliance_check
from app.models.schemas import ComplianceReport

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/gaps", response_model=ComplianceReport)
def get_compliance_gaps() -> ComplianceReport:
    try:
        return run_compliance_check()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
