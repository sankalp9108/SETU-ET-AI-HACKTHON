"""
Shared Cypher queries for agents — Phase 6.

Kept separate from graph/writer.py (which only writes) and graph/schema.py
(which only defines labels/constraints) so agent-facing read queries have
one home, reusable across RCA, Compliance, and Lessons-Learned as they're
built in later phases.

IMPORTANT — current limitation: this queries for :Equipment, :WorkOrder, and
:IncidentReport nodes, none of which exist yet (entity extraction, the LLM
step that would populate them, hasn't been built — see README.md). Right
now, every call here will correctly return an empty list, not an error.
That's expected: the query is written against the target schema
(docs/data_model_conventions.md) so agents/rca.py doesn't need to change
once entity extraction adds real data — only this file's queries will
suddenly start returning real results.
"""

from app.graph.writer import get_driver


def get_equipment_history(equipment_id: str) -> list[dict]:
    """Pulls every WorkOrder and IncidentReport connected to an Equipment
    node, each with its source document filename if traceable. Returns a
    flat list of event dicts, UNSORTED (agents/rca.py sorts chronologically)
    so this function stays a pure data-fetch with no business logic.

    Each dict: {event_type, date, description, source_document}
    """
    driver = get_driver()
    events: list[dict] = []

    with driver.session() as session:
        # Work orders that maintained this equipment, plus their source doc.
        wo_result = session.run(
            """
            MATCH (wo:WorkOrder)-[:MAINTAINED_BY]->(e:Equipment {id: $equipment_id})
            OPTIONAL MATCH (wo)-[:DOCUMENTED_IN]->(doc:Document)
            RETURN wo.id AS id, wo.date AS date, wo.description AS description,
                   doc.filename AS source_document
            """,
            equipment_id=equipment_id,
        )
        for record in wo_result:
            events.append(
                {
                    "event_type": "work_order",
                    "date": record["date"],
                    "description": record["description"] or f"Work order {record['id']}",
                    "source_document": record["source_document"],
                }
            )

        # Incident reports for this equipment, plus the work order (and its
        # source doc) they were documented in, if any.
        ir_result = session.run(
            """
            MATCH (ir:IncidentReport)-[:HAD_FAILURE]->(e:Equipment {id: $equipment_id})
            OPTIONAL MATCH (ir)-[:DOCUMENTED_IN]->(wo:WorkOrder)-[:DOCUMENTED_IN]->(doc:Document)
            RETURN ir.id AS id, ir.date AS date, ir.description AS description,
                   ir.severity AS severity, ir.root_cause AS root_cause,
                   doc.filename AS source_document
            """,
            equipment_id=equipment_id,
        )
        for record in ir_result:
            description = record["description"] or f"Incident {record['id']}"
            if record["root_cause"]:
                description += f" (root cause: {record['root_cause']})"
            events.append(
                {
                    "event_type": "incident",
                    "date": record["date"],
                    "description": description,
                    "source_document": record["source_document"],
                }
            )

    return events


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.graph.queries <equipment_id>")
        sys.exit(1)

    history = get_equipment_history(sys.argv[1])
    print(f"Found {len(history)} events for equipment {sys.argv[1]}")
    for e in history:
        print(f"  [{e['event_type']}] {e['date']}: {e['description']} (source: {e['source_document']})")
