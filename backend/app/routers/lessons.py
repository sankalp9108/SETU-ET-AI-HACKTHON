"""
Lessons-Learned router — Phase 8.

POST /lessons/check — takes a new incident description and returns alerts
for similar past incidents. (The original todo sketch had this as a
no-input GET /lessons/alerts, but the agent's actual job — comparing a NEW
incident against PAST ones — needs a description as input, so this is a
POST with a request body instead.)
"""

from fastapi import APIRouter, HTTPException

from app.agents.lessons_learned import check_lessons_learned
from app.models.schemas import LessonsLearnedRequest, LessonsLearnedReport

router = APIRouter(prefix="/lessons", tags=["lessons-learned"])


@router.post("/check", response_model=LessonsLearnedReport)
def check_lessons(request: LessonsLearnedRequest) -> LessonsLearnedReport:
    try:
        return check_lessons_learned(request.incident_description)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
