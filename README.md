# SETU — Unified Industrial Knowledge Intelligence Platform

**सेतु (Setu) — "bridge."** One connected knowledge brain across every fragmented document,
drawing, work order, and lesson a plant has ever recorded — queryable in seconds, from any
device.

Built for the **ET AI Hackathon 2026**, theme: *AI for Industrial Knowledge Intelligence*.

---

## The problem

Industrial plants aren't short on information — they're short on *access* to it at the moment a
decision has to be made:

- **~$260,000/hour** is the average cost of unplanned downtime across manufacturing.
- **72%** of manufacturers report "hidden factories" of undocumented fixes — meaning even the
  organizations tracking this problem don't have a full picture of it.
- **49%** of plants run a CMMS/EAM *and* parallel spreadsheets anyway — the system of record and
  the actual working knowledge have diverged.
- **~40%** of the global maintenance workforce is expected to retire by 2030, taking undocumented
  tacit knowledge with them.
- Root cause, in one line: the tools built to manage industrial knowledge (CMMS/EAM, drawing
  archives, QMS, email) were each built to manage **one type of record** — none connect a P&ID, a
  work order, a procedure, and an incident report about the same physical asset into one
  answerable question.

## The solution

SETU is one ingestion pipeline feeding one shared knowledge core (a Neo4j knowledge graph plus a
PostgreSQL/pgvector store), with every user-facing "agent" being a different reasoning lens over
that same data — not five disconnected point tools. A field technician's phone query and an
engineer's root-cause investigation draw on the exact same graph, so an answer given in the field
is provably consistent with what an engineer would find at a desktop.

| Agent | Answers |
|---|---|
| **Copilot** | "What does the SOP say about X?" — instant, cited, plain-language Q&A |
| **RCA** (Root Cause Analysis) | "Why does this equipment keep failing?" — a timeline synthesized from work order and incident history |
| **Compliance** | "Are our procedures missing anything they should reference?" — automatic gap detection against safety/permit policies |
| **Lessons-Learned** | "Has this happened before?" — surfaces similar past incidents before they repeat |

Every answer carries a source citation and a confidence score — the system is built to say "I
don't know" rather than answer without grounding.

---

## Repo structure

This is a monorepo containing both halves of the application:

```text
setu/
├── backend/          FastAPI service — ingestion, knowledge graph, vector store, all 4 agents
│   ├── app/
│   │   ├── ingestion/      PDF (born-digital + OCR), DOCX, and spreadsheet parsing
│   │   ├── graph/          Neo4j schema, writer, and agent-facing Cypher queries
│   │   ├── vectorstore/    Postgres/pgvector storage and embedding (Google Gemini)
│   │   ├── retrieval/      GraphRAG (vector + graph fusion) and Self-RAG grading
│   │   ├── agents/         Copilot, RCA, Compliance, Lessons-Learned
│   │   ├── routers/        FastAPI endpoints, one per agent
│   │   ├── models/         Pydantic request/response schemas (the API contract)
│   │   └── main.py         FastAPI app entry point
│   ├── migrations/         Neo4j constraint scripts + Postgres schema SQL
│   ├── docs/               API_REFERENCE.md and other build documentation
│   ├── source_documents/   Where ingested plant documents live, organized by type
│   ├── docker-compose.yml  Neo4j + Postgres containers
│   └── requirements.txt
│
└── frontend/          TanStack Start (React 19) app consuming the backend API
    ├── src/
    │   ├── api/            Typed HTTP client, one file per agent endpoint
    │   ├── types/           TypeScript interfaces mirroring the backend's Pydantic schemas
    │   ├── hooks/           React Query hooks wrapping the API layer
    │   ├── components/      Shared UI: AppShell, EmptyState, ErrorBanner, Timeline, badges, etc.
    │   └── routes/          File-based routes — Copilot, RCA, Compliance, Lessons-Learned, Graph
    └── package.json
```

Each folder has its own dependencies and is run independently — see **Getting Started** below.

---

## Architecture

```
 Mobile field app          Desktop console
 (technicians)              (engineers/managers)
        │                          │
        └──────────┬───────────────┘
                    ▼
         Frontend (TanStack Start)
                    │  REST calls
                    ▼
         FastAPI backend
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
   Copilot        RCA        Compliance      Lessons-Learned
        │           │            │                 │
        └─────┬─────┴─────┬──────┴─────────┬───────┘
              ▼           ▼                ▼
      GraphRAG retrieval (vector + graph, run concurrently)
              │                            │
              ▼                            ▼
     PostgreSQL + pgvector          Neo4j knowledge graph
     (chunked text, embeddings)     (entities & relationships)
              ▲                            ▲
              └──────────────┬─────────────┘
                              │
                    Ingestion pipeline
        (intake → parse/OCR → chunk → embed → store)
                              │
                              ▼
                    source_documents/
       (P&IDs, work orders, procedures, inspections,
              incidents, policies, manuals)
```

---

## Tech stack

### Backend
| Layer | Choice |
|---|---|
| API framework | FastAPI (Python) |
| Knowledge graph | Neo4j |
| Vector store | PostgreSQL + pgvector |
| Embeddings | Google Gemini (`gemini-embedding-001`) |
| LLM reasoning | Provider-agnostic — Gemini, Anthropic, or OpenAI, auto-selected by whichever API key is configured |
| Document parsing | PyMuPDF/pdfplumber (PDF), Tesseract + OpenCV (scanned/OCR), python-docx (Word), pandas/openpyxl (spreadsheets) |
| Retrieval | GraphRAG (concurrent vector + graph fusion) with Self-RAG relevance grading |

### Frontend
| Layer | Choice |
|---|---|
| Framework | TanStack Start (React 19), file-based routing |
| Data fetching | TanStack Query (React Query) |
| HTTP client | axios |
| Styling | Tailwind CSS v4 |
| Component primitives | shadcn/ui (Radix UI) |
| Forms/validation | react-hook-form + zod |
| Charts | recharts |
| Icons | lucide-react |

---

## Getting started

### 1. Backend

```bash
cd backend
cp .env.example .env
# Fill in: GEMINI_API_KEY (or ANTHROPIC_API_KEY / OPENAI_API_KEY), EMBEDDING_PROVIDER=google, etc.

pip install -r requirements.txt

docker-compose up -d              # Neo4j + Postgres
python -m app.graph.migrate       # apply Neo4j constraints
python -m app.vectorstore.migrate # apply Postgres schema

# Add documents to source_documents/<type>/, then:
python -m app.ingestion.intake     # dry-run check
python -m app.ingestion.pipeline   # parse, chunk, embed, store

uvicorn app.main:app --reload --port 8000
```

Full API contract: [`backend/docs/API_REFERENCE.md`](./backend/docs/API_REFERENCE.md). Interactive
docs at `http://localhost:8000/docs` once running.

### 2. Frontend

```bash
cd frontend
bun install       # or npm install
# Set VITE_API_BASE_URL=http://localhost:8000 in .env

bun dev           # or npm run dev
```

The frontend expects the backend to be running and reachable at `VITE_API_BASE_URL`.

---

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check |
| `/copilot/query` | POST | Ask a natural-language question |
| `/rca/query` | POST | Root cause analysis for an equipment ID |
| `/compliance/gaps` | GET | Scan ingested documents for compliance gaps |
| `/lessons/check` | POST | Find similar past incidents to a new one |

Full request/response shapes, error formats, and examples are documented in
[`backend/docs/API_REFERENCE.md`](./backend/docs/API_REFERENCE.md).

---

## Known limitations

Being upfront about where this MVP currently stands:

- **No LLM entity extraction yet.** The knowledge graph currently holds only `Document` nodes —
  structured `Equipment`/`WorkOrder`/`IncidentReport` nodes and their relationships
  (`MAINTAINED_BY`, `HAD_FAILURE`, etc.) haven't been populated yet. This means:
  - `/rca/query` currently returns `insufficient_data: true` for every equipment ID.
  - The graph-side half of retrieval falls back to a filename keyword match rather than real
    relationship traversal.
- **`/lessons/check`** needs at least one incident report ingested to return anything —none have
  been added to the demo corpus yet.
- **`/copilot/query` and `/compliance/gaps` work fully today** with whatever documents have been
  ingested — no entity extraction dependency for either.
- **No graph visualization endpoint yet** — the frontend's `/graph` screen is a placeholder until
  the backend exposes raw nodes/edges.
- **No authentication, no rate limiting, no multi-tenant support** — out of scope for this
  hackathon MVP by design.

---

## Roadmap (pitched, not built)

- LLM-based entity extraction — unlocks full RCA and richer Compliance/Lessons-Learned reasoning
- Live IoT/sensor integration
- Voice input for hands-free field queries
- Tacit-knowledge capture from retiring engineers (structured interview/voice capture)
- Multi-plant deployment with per-plant graphs and a cross-plant lessons-learned layer

---

## License / context

Built as a hackathon submission for the ET AI Hackathon 2026. Not currently intended for
production/regulated deployment without further security, compliance, and access-control work
(see backend documentation for the security model this MVP is scoped against).
