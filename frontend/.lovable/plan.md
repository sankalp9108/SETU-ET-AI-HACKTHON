# SETU Frontend Build Plan

Build a TanStack Start frontend consuming the FastAPI backend at `VITE_API_BASE_URL` (default `http://localhost:8000`). Five screens: Copilot, Compliance, RCA, Lessons-Learned, Graph. Every screen must handle loading, error, and `insufficient_data`/`insufficient_evidence` states as first-class UI.

Note: this project uses **TanStack Start (file-based routing under `src/routes/`)**, not the Vite + react-router-dom scaffold in the source plan. I'll adapt Phase 0 routing to TanStack Router but keep every other phase intact.

## Design direction

Field-first + engineer-desktop. Restrained palette — deep slate background, warm off-white surfaces, single amber accent for actions, semantic reds/oranges/yellows only for severity badges. Typography: Inter for UI, JetBrains Mono for equipment IDs / citations. Mobile-first layouts, generous touch targets, bottom nav on mobile / left rail on desktop.

## Structure

```text
src/
  api/          client.ts, copilot.ts, rca.ts, compliance.ts, lessons.ts
  types/        copilot.ts, rca.ts, compliance.ts, lessons.ts
  hooks/        useCopilotQuery, useRcaQuery, useComplianceGaps, useLessonsCheck, useHealth
  components/   AppShell, Badge, CitationList, ConfidenceBar, EmptyState,
                LoadingSpinner, ErrorBanner, Timeline, HealthIndicator
  routes/       __root.tsx (AppShell), index.tsx (Copilot),
                compliance.tsx, rca.tsx, lessons.tsx, graph.tsx
```

## Phases (condensed)

1. **Setup**: add `axios`, `recharts`, `lucide-react` (already have React Query + Tailwind v4 + TanStack Router). Add `VITE_API_BASE_URL` handling with fallback. Define design tokens in `src/styles.css` (slate/amber palette, mono font via `<link>` in `__root`).
2. **Types + API client**: mirror `docs/API_REFERENCE.md` field-for-field. Shared axios instance + one `parseApiError` helper covering 503 `{detail}` and 422 validation-array shapes. No `any` on responses.
3. **Shared components**: Badge (severity), CitationList, ConfidenceBar, EmptyState (framed as "nothing found yet", not error), LoadingSpinner + skeletons, ErrorBanner (shows backend `detail`), AppShell with responsive nav (left rail ≥md, bottom tab bar <md), HealthIndicator polling `/health`.
4. **Copilot screen** (`/`): chat layout, input pinned bottom on mobile, scrollable history, renders answer + citations + confidence bar; `insufficient_evidence` → EmptyState instead of "0.0 confidence".
5. **Compliance screen** (`/compliance`): grouped by severity CRITICAL→HIGH→MEDIUM, cards show filename, description, evidence, regulation reference (or "no matching regulatory document"). Distinct states: `gaps: []` + `insufficient_data:false` = positive "no gaps found"; `insufficient_data:true` = "not enough documents ingested". Shows `documents_checked` / `regulatory_documents_used` in header.
6. **RCA screen** (`/rca`): equipment ID input, vertical Timeline component with icon per `event_type`, prominent `failure_summary` / `contributing_factors` / `recommendation`. Full `insufficient_data` empty state reusing backend explanation text.
7. **Lessons-Learned screen** (`/lessons`): textarea + submit, alert cards with similarity bar, excerpt, highlighted `shared_equipment_ids`, note. Same `insufficient_data` handling.
8. **Graph screen** (`/graph`): placeholder screen with clear "endpoint not yet available on backend" empty state (no `react-force-graph` install until endpoint exists — flagged in source plan as blocked). Route exists so nav is complete.
9. **Shell polish**: nav highlights active route, back/forward works, HealthIndicator in header, consistent loading/error/empty across all screens.
10. **Mobile pass**: verify 375px for every screen; Copilot most important.
11. **Error handling**: 503 → ErrorBanner + retry; 422 → prevented client-side by disabling submit on empty, handled if slips through; network failure distinct from 503; never raw JSON to user.
12. **SEO/meta**: real title + description per route in `head()`; replace "Lovable App" defaults; add sitemap.xml + robots.txt.

## Not in scope

- Mock data — every screen calls the real backend.
- Auth (backend has none per the API contract described).
- Graph rendering itself (blocked on new backend endpoint).
- Ingestion UI (out of scope of the source plan).

## Verification

Manual: cURL each endpoint to confirm response shapes before wiring, then click through each screen against a running backend at `http://localhost:8000`. Confirm empty states render when backend returns `insufficient_data:true`. Typecheck passes with zero `any` on API boundaries.
