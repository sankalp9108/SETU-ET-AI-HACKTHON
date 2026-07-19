// SETU — Neo4j constraints (migration 001)
// Paste directly into Neo4j Browser if you'd rather apply manually than run
// `python -m app.graph.migrate`. Safe to re-run — all use IF NOT EXISTS.

CREATE CONSTRAINT equipment_id_unique IF NOT EXISTS FOR (e:Equipment) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT work_order_id_unique IF NOT EXISTS FOR (w:WorkOrder) REQUIRE w.id IS UNIQUE;
CREATE CONSTRAINT incident_report_id_unique IF NOT EXISTS FOR (i:IncidentReport) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT personnel_id_unique IF NOT EXISTS FOR (p:Personnel) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT regulatory_reference_id_unique IF NOT EXISTS FOR (r:RegulatoryReference) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT procedure_id_unique IF NOT EXISTS FOR (p:Procedure) REQUIRE p.id IS UNIQUE;
