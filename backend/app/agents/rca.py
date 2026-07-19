"""
RCA (Root Cause Analysis) agent — Phase 6.

Pipeline: equipment_id -> graph/queries.get_equipment_history()
  -> if no records exist: return an explicit insufficient_data response
     (honest limitation right now — entity extraction hasn't been built yet,
     so the graph has no Equipment/WorkOrder/IncidentReport nodes to find;
     see app/graph/queries.py's docstring)
  -> else: sort chronologically -> LLM synthesizes a structured RCA report
     -> citations computed from code (source documents actually in the
        traversed history), same enforcement pattern as the Copilot agent
"""

import json

from app.config import LLM_MODEL_REASONING
from app.llm_client import generate_text
from app.graph.queries import get_equipment_history
from app.models.schemas import RCAQueryResponse, RCATimelineEntry

NO_DATA_MESSAGE = (
    "No work orders or incident reports are linked to equipment '{equipment_id}' "
    "in the knowledge graph yet. This could mean the equipment ID doesn't exist "
    "in your ingested documents, or that entity extraction (which populates "
    "these graph relationships) hasn't been run yet."
)


def _sort_chronologically(events: list[dict]) -> list[dict]:
    """Sorts by date ascending. Events with no date (None) are pushed to the
    end rather than crashing a sort comparison or being silently dropped."""
    dated = [e for e in events if e.get("date")]
    undated = [e for e in events if not e.get("date")]
    dated.sort(key=lambda e: e["date"])
    return dated + undated


def _build_citations(events: list[dict]) -> list[str]:
    """Unique source document filenames actually present in the traversed
    history — not decided by the LLM, so a citation always traces back to a
    real graph-linked document."""
    seen = []
    for e in events:
        doc = e.get("source_document")
        if doc and doc not in seen:
            seen.append(doc)
    return seen


def _build_rca_prompt(equipment_id: str, timeline_text: str) -> str:
    return f"""You are a maintenance root-cause-analysis assistant. Given the
chronological equipment history below for equipment '{equipment_id}', produce
a structured root cause analysis.

Equipment history (chronological):
{timeline_text}

Respond with ONLY a JSON object, no other text, in this exact shape:
{{
  "failure_summary": "2-3 sentence summary of what happened",
  "contributing_factors": ["factor 1", "factor 2"],
  "recommendation": "1-2 sentence actionable recommendation"
}}

Base this ONLY on the history given above — do not invent details not present in it."""


def get_rca_report(equipment_id: str) -> RCAQueryResponse:
    """Main RCA entry point. Synchronous — graph_queries and generate_text
    are both synchronous calls, no concurrent retrieval needed here (unlike
    Copilot, there's only one data source: the graph)."""
    events = get_equipment_history(equipment_id)

    if not events:
        return RCAQueryResponse(
            equipment_id=equipment_id,
            failure_summary=NO_DATA_MESSAGE.format(equipment_id=equipment_id),
            timeline=[],
            contributing_factors=[],
            recommendation="Ensure this equipment ID has been ingested and entity "
                           "extraction has run before requesting an RCA report.",
            citations=[],
            insufficient_data=True,
        )

    sorted_events = _sort_chronologically(events)
    timeline_text = "\n".join(
        f"- [{e['event_type']}] {e['date'] or 'undated'}: {e['description']}"
        for e in sorted_events
    )

    prompt = _build_rca_prompt(equipment_id, timeline_text)
    raw_response = generate_text(prompt, model=LLM_MODEL_REASONING, max_tokens=600).strip()
    raw_response = raw_response.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(raw_response)
        failure_summary = parsed.get("failure_summary", "").strip()
        contributing_factors = parsed.get("contributing_factors", [])
        recommendation = parsed.get("recommendation", "").strip()
    except json.JSONDecodeError:
        # LLM didn't return parseable JSON — fail safe with the raw text as
        # the summary rather than crashing the whole request.
        failure_summary = raw_response
        contributing_factors = []
        recommendation = "Unable to parse a structured recommendation — see failure_summary."

    timeline = [
        RCATimelineEntry(
            date=e["date"],
            event_type=e["event_type"],
            description=e["description"],
            source_document=e["source_document"],
        )
        for e in sorted_events
    ]

    return RCAQueryResponse(
        equipment_id=equipment_id,
        failure_summary=failure_summary,
        timeline=timeline,
        contributing_factors=contributing_factors,
        recommendation=recommendation,
        citations=_build_citations(sorted_events),
        insufficient_data=False,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.agents.rca <equipment_id>")
        sys.exit(1)

    result = get_rca_report(sys.argv[1])
    print(f"Equipment: {result.equipment_id}")
    print(f"Insufficient data: {result.insufficient_data}\n")
    print(f"Summary: {result.failure_summary}\n")
    print("Timeline:")
    for entry in result.timeline:
        print(f"  [{entry.event_type}] {entry.date}: {entry.description} (source: {entry.source_document})")
    print(f"\nContributing factors: {result.contributing_factors}")
    print(f"Recommendation: {result.recommendation}")
    print(f"Citations: {result.citations}")
