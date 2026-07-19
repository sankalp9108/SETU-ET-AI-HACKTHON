"""
SETU FastAPI app — Phase 5.

First real API surface. Only /copilot/query exists so far (Phase 5); RCA,
Compliance, and Lessons-Learned routers get added the same way in Phases
6-8 — each is its own router module, included here.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routers import copilot, rca, compliance, lessons

app = FastAPI(
    title="SETU Backend",
    description="Unified Industrial Knowledge Intelligence Platform — backend API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(copilot.router)
app.include_router(rca.router)
app.include_router(compliance.router)
app.include_router(lessons.router)


@app.get("/health")
def health_check():
    """Basic liveness check — does NOT verify Neo4j/Postgres/LLM connectivity,
    just that the FastAPI process itself is up."""
    return {"status": "ok", "service": "setu-backend"}


@app.get("/")
def root():
    """API discovery endpoint for frontend developers — see docs/API_REFERENCE.md
    for full request/response schemas, or /docs for interactive Swagger UI."""
    return {
        "service": "setu-backend",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "copilot": "POST /copilot/query",
            "rca": "POST /rca/query",
            "compliance": "GET /compliance/gaps",
            "lessons_learned": "POST /lessons/check",
        },
    }
