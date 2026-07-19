"""
Neo4j schema definition for SETU.

This module is the single source of truth for node labels and relationship
types used across the ingestion pipeline (graph/writer.py) and every agent's
Cypher queries (graph/queries.py). Import constants from here rather than
hardcoding label/relationship strings elsewhere — a typo in a hardcoded label
silently creates a new, disconnected node type instead of erroring.
"""

# --- Node labels ---
NODE_EQUIPMENT = "Equipment"
NODE_WORK_ORDER = "WorkOrder"
NODE_PROCEDURE = "Procedure"
NODE_INCIDENT_REPORT = "IncidentReport"
NODE_PERSONNEL = "Personnel"
NODE_REGULATORY_REFERENCE = "RegulatoryReference"
NODE_DOCUMENT = "Document"

ALL_NODE_LABELS = [
    NODE_EQUIPMENT,
    NODE_WORK_ORDER,
    NODE_PROCEDURE,
    NODE_INCIDENT_REPORT,
    NODE_PERSONNEL,
    NODE_REGULATORY_REFERENCE,
    NODE_DOCUMENT,
]

# --- Relationship types ---
REL_MAINTAINED_BY = "MAINTAINED_BY"        # (WorkOrder)-[:MAINTAINED_BY]->(Equipment)
REL_REPORTED_BY = "REPORTED_BY"            # (WorkOrder)-[:REPORTED_BY]->(Personnel)
REL_HAD_FAILURE = "HAD_FAILURE"            # (IncidentReport)-[:HAD_FAILURE]->(Equipment)
REL_DOCUMENTED_IN = "DOCUMENTED_IN"        # (IncidentReport|WorkOrder)-[:DOCUMENTED_IN]->(WorkOrder|Document)
REL_FOLLOWS_PROCEDURE = "FOLLOWS_PROCEDURE"  # (Equipment)-[:FOLLOWS_PROCEDURE]->(Procedure)
REL_REFERENCES = "REFERENCES"              # (Procedure)-[:REFERENCES]->(RegulatoryReference)
REL_LOCATED_IN = "LOCATED_IN"              # (Equipment)-[:LOCATED_IN {zone}]->(Equipment), optional parent/child

ALL_RELATIONSHIP_TYPES = [
    REL_MAINTAINED_BY,
    REL_REPORTED_BY,
    REL_HAD_FAILURE,
    REL_DOCUMENTED_IN,
    REL_FOLLOWS_PROCEDURE,
    REL_REFERENCES,
    REL_LOCATED_IN,
]

# --- Uniqueness constraints ---
# Every entity node is MERGEd on these keys during ingestion (graph/writer.py)
# so re-ingesting the same source document never creates duplicate nodes.
CONSTRAINTS_CYPHER = [
    f"CREATE CONSTRAINT equipment_id_unique IF NOT EXISTS "
    f"FOR (e:{NODE_EQUIPMENT}) REQUIRE e.id IS UNIQUE;",

    f"CREATE CONSTRAINT work_order_id_unique IF NOT EXISTS "
    f"FOR (w:{NODE_WORK_ORDER}) REQUIRE w.id IS UNIQUE;",

    f"CREATE CONSTRAINT incident_report_id_unique IF NOT EXISTS "
    f"FOR (i:{NODE_INCIDENT_REPORT}) REQUIRE i.id IS UNIQUE;",

    f"CREATE CONSTRAINT personnel_id_unique IF NOT EXISTS "
    f"FOR (p:{NODE_PERSONNEL}) REQUIRE p.id IS UNIQUE;",

    f"CREATE CONSTRAINT regulatory_reference_id_unique IF NOT EXISTS "
    f"FOR (r:{NODE_REGULATORY_REFERENCE}) REQUIRE r.id IS UNIQUE;",

    f"CREATE CONSTRAINT document_id_unique IF NOT EXISTS "
    f"FOR (d:{NODE_DOCUMENT}) REQUIRE d.id IS UNIQUE;",

    # Procedure isn't in the original build-plan constraint list, but it needs
    # one too — otherwise MERGE-ing the same SOP from two documents (e.g. a
    # policy PDF and a cross-referencing work order) will duplicate it.
    f"CREATE CONSTRAINT procedure_id_unique IF NOT EXISTS "
    f"FOR (p:{NODE_PROCEDURE}) REQUIRE p.id IS UNIQUE;",
]


def get_constraint_statements() -> list[str]:
    """Returns the list of Cypher statements to run once, at startup / migration time."""
    return CONSTRAINTS_CYPHER


# --- Reference schema (for docstrings / onboarding, not executed) ---
SCHEMA_REFERENCE_CYPHER = """
// Node labels (with key properties)
(:Equipment {id, name, type, location, status})
(:WorkOrder {id, date, type, description})
(:Procedure {id, title, category})
(:IncidentReport {id, date, severity, description, root_cause})
(:Personnel {id, name, role, years_experience})
(:RegulatoryReference {id, code, category})
(:Document {id, filename, doc_type, ingested_at})

// Relationships
(:WorkOrder)-[:MAINTAINED_BY]->(:Equipment)
(:WorkOrder)-[:REPORTED_BY]->(:Personnel)
(:IncidentReport)-[:HAD_FAILURE]->(:Equipment)
(:IncidentReport)-[:DOCUMENTED_IN]->(:WorkOrder)
(:Equipment)-[:FOLLOWS_PROCEDURE]->(:Procedure)
(:Procedure)-[:REFERENCES]->(:RegulatoryReference)
(:Equipment)-[:LOCATED_IN {zone}]->(:Equipment)
(:WorkOrder)-[:DOCUMENTED_IN]->(:Document)
"""
