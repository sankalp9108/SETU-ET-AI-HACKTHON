"""
Pydantic schemas — Phase 5 (Copilot agent + API contract).

These are the exact shapes the frontend should expect from /copilot/query.
Keeping them in one place so the API contract is unambiguous and reusable
by later agents (RCA, Compliance, Lessons-Learned) that share the same
citation/confidence pattern.
"""

from pydantic import BaseModel, Field


class CopilotQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's natural-language question")


class CopilotQueryResponse(BaseModel):
    answer: str
    citations: list[str] = Field(
        default_factory=list,
        description="Filenames of source documents the answer is grounded in",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="0.0-1.0 — derived from retrieval similarity scores of the "
                     "chunks actually used, not a model self-report",
    )
    insufficient_evidence: bool = Field(
        default=False,
        description="True if no relevant evidence was found — 'answer' will be "
                     "an explicit I-don't-know rather than a guess",
    )


class RCAQueryRequest(BaseModel):
    equipment_id: str = Field(..., min_length=1, description="e.g. 'P204', 'C101'")


class RCATimelineEntry(BaseModel):
    date: str | None = None
    event_type: str  # "work_order" | "incident"
    description: str
    source_document: str | None = None


class RCAQueryResponse(BaseModel):
    equipment_id: str
    failure_summary: str
    timeline: list[RCATimelineEntry] = Field(default_factory=list)
    contributing_factors: list[str] = Field(default_factory=list)
    recommendation: str
    citations: list[str] = Field(default_factory=list)
    insufficient_data: bool = Field(
        default=False,
        description="True if no WorkOrder/IncidentReport records exist for this "
                     "equipment in the graph yet — 'failure_summary' explains why "
                     "rather than fabricating a report",
    )


class ComplianceGap(BaseModel):
    document_filename: str
    doc_type: str
    regulation_reference: str | None = Field(
        default=None,
        description="Filename of the regulatory/policy document this gap relates "
                     "to, if identifiable — None if no matching regulatory doc exists",
    )
    severity: str = Field(description="CRITICAL | HIGH | MEDIUM")
    description: str
    evidence: str = Field(description="The specific text/absence that triggered this gap")


class ComplianceReport(BaseModel):
    gaps: list[ComplianceGap] = Field(default_factory=list)
    documents_checked: int = 0
    regulatory_documents_used: list[str] = Field(default_factory=list)
    insufficient_data: bool = Field(
        default=False,
        description="True if there are no checkable documents or no regulatory "
                     "documents ingested yet",
    )
    note: str = ""


class LessonsLearnedRequest(BaseModel):
    incident_description: str = Field(
        ..., min_length=1,
        description="Description of a new/current incident to check against past ones",
    )


class LessonsLearnedAlert(BaseModel):
    filename: str
    similarity: float
    excerpt: str
    shared_equipment_ids: list[str] = Field(default_factory=list)
    note: str


class LessonsLearnedReport(BaseModel):
    query: str
    alerts: list[LessonsLearnedAlert] = Field(default_factory=list)
    insufficient_data: bool = Field(
        default=False,
        description="True if no past incident documents have been ingested yet",
    )
    note: str = ""
