"""
Compliance agent — Phase 7.

Unlike RCA, this does NOT need entity extraction (Equipment/WorkOrder graph
nodes) to do real work — it operates directly on `documents.doc_type`,
which has existed since Phase 3 ingestion. The "regulatory subset" here is
whatever your ingested policy/permit-to-work/emergency-plan documents
actually say, not a curated OISD/PESO/Factory-Act corpus (that's a future
extension — see docs/source_documents_mapping.md's "still needed" list).

Pipeline: split ingested documents into REGULATORY_DOC_TYPES (the "regulatory
subset" to check against) and CHECKABLE_DOC_TYPES (documents that should
reference/comply with them) -> for each checkable document, ask the LLM to
identify compliance gaps against the regulatory subset -> return a
structured report.

If either side is empty (no regulatory docs ingested yet, or no checkable
docs), returns insufficient_data=True rather than fabricating gaps.
"""

import json

from app.config import LLM_MODEL_REASONING
from app.llm_client import generate_text
from app.vectorstore.store import get_connection, get_documents_by_doc_types, get_document_full_text
from app.models.schemas import ComplianceGap, ComplianceReport

# The "regulatory subset" — documents that establish requirements.
REGULATORY_DOC_TYPES = ["policy", "permit_to_work", "emergency_plan", "ppe_policy"]

# Documents that should be checked for gaps against the regulatory subset.
CHECKABLE_DOC_TYPES = ["procedure", "oem_manual", "admin"]

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM"}


def _build_compliance_prompt(check_doc_text: str, check_doc_filename: str, regulatory_docs: list[dict]) -> str:
    regulatory_summary = "\n\n".join(
        f"[{doc['filename']}]\n{doc['text'][:2000]}" for doc in regulatory_docs
    )
    return f"""You are a plant safety compliance auditor. Compare the procedure
document below against the regulatory/policy documents that should govern it,
and identify any compliance gaps — places where the procedure should
reference a requirement (e.g. Permit to Work, PPE, confined space entry) but
doesn't, or contradicts a regulatory document.

Regulatory/policy documents:
{regulatory_summary}

Procedure document to check ("{check_doc_filename}"):
{check_doc_text[:3000]}

Respond with ONLY a JSON array of gaps found (empty array if none), no other
text, in this exact shape:
[{{
  "regulation_reference": "filename of the regulatory doc this relates to, or null",
  "severity": "CRITICAL" | "HIGH" | "MEDIUM",
  "description": "what the gap is",
  "evidence": "the specific text or absence that shows this gap"
}}, ...]

Only flag genuine gaps grounded in the documents given — do not invent requirements
not present in the regulatory documents above."""


def _check_one_document(check_doc: dict, regulatory_docs: list[dict]) -> list[ComplianceGap]:
    conn = get_connection()
    try:
        check_text = get_document_full_text(conn, check_doc["id"])
    finally:
        conn.close()

    if not check_text.strip():
        return []

    prompt = _build_compliance_prompt(check_text, check_doc["filename"], regulatory_docs)
    raw = generate_text(prompt, model=LLM_MODEL_REASONING, max_tokens=800).strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed_gaps = json.loads(raw)
    except json.JSONDecodeError:
        # Fail safe: skip this document's gaps rather than crashing the
        # whole report over one malformed LLM response.
        return []

    gaps = []
    for g in parsed_gaps:
        severity = g.get("severity", "MEDIUM")
        if severity not in VALID_SEVERITIES:
            severity = "MEDIUM"
        gaps.append(
            ComplianceGap(
                document_filename=check_doc["filename"],
                doc_type=check_doc["doc_type"],
                regulation_reference=g.get("regulation_reference"),
                severity=severity,
                description=g.get("description", ""),
                evidence=g.get("evidence", ""),
            )
        )
    return gaps


def run_compliance_check() -> ComplianceReport:
    """Main entry point. Fetches the regulatory subset and checkable
    documents from Postgres, then runs one LLM call per checkable document
    (not one call for the whole corpus at once — keeps each prompt focused
    and avoids truncating a large regulatory corpus into one context)."""
    conn = get_connection()
    try:
        regulatory_doc_refs = get_documents_by_doc_types(conn, REGULATORY_DOC_TYPES)
        checkable_doc_refs = get_documents_by_doc_types(conn, CHECKABLE_DOC_TYPES)

        regulatory_docs = [
            {**doc, "text": get_document_full_text(conn, doc["id"])}
            for doc in regulatory_doc_refs
        ]
    finally:
        conn.close()

    if not regulatory_docs or not checkable_doc_refs:
        missing = []
        if not regulatory_docs:
            missing.append("no regulatory/policy documents ingested yet")
        if not checkable_doc_refs:
            missing.append("no procedure/SOP documents ingested yet")
        return ComplianceReport(
            gaps=[],
            documents_checked=0,
            regulatory_documents_used=[],
            insufficient_data=True,
            note="Cannot run a compliance check: " + "; ".join(missing) + ". "
                 "Ingest documents into the folders mapped in "
                 "docs/source_documents_mapping.md and try again.",
        )

    all_gaps: list[ComplianceGap] = []
    for check_doc in checkable_doc_refs:
        all_gaps.extend(_check_one_document(check_doc, regulatory_docs))

    return ComplianceReport(
        gaps=all_gaps,
        documents_checked=len(checkable_doc_refs),
        regulatory_documents_used=[d["filename"] for d in regulatory_docs],
        insufficient_data=False,
        note="",
    )


if __name__ == "__main__":
    report = run_compliance_check()
    print(f"Documents checked: {report.documents_checked}")
    print(f"Regulatory documents used: {report.regulatory_documents_used}")
    print(f"Insufficient data: {report.insufficient_data}")
    if report.note:
        print(f"Note: {report.note}")
    print(f"\nGaps found: {len(report.gaps)}")
    for gap in report.gaps:
        print(f"  [{gap.severity}] {gap.document_filename}: {gap.description}")
        print(f"    Evidence: {gap.evidence}")
        print(f"    Regulation reference: {gap.regulation_reference}")
