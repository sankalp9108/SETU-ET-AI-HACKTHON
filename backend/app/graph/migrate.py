"""
One-time Neo4j migration: applies the uniqueness constraints from schema.py.

Run this once after `docker-compose up` brings Neo4j up (and any time the
constraint list in schema.py changes):

    python -m app.graph.migrate

Idempotent — every statement uses `IF NOT EXISTS`, so re-running is safe.
"""

from neo4j import GraphDatabase

from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from app.graph.schema import get_constraint_statements


def run_migration() -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
        print(f"Connected to Neo4j at {NEO4J_URI}")

        with driver.session() as session:
            for statement in get_constraint_statements():
                session.run(statement)
                print(f"Applied: {statement}")

        with driver.session() as session:
            result = session.run("SHOW CONSTRAINTS")
            print("\nCurrent constraints:")
            for record in result:
                print(f"  - {record.get('name')}")
    finally:
        driver.close()


if __name__ == "__main__":
    run_migration()
