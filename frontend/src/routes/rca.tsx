import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Wrench, Search, ListChecks } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Timeline } from "@/components/Timeline";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { useRcaQuery } from "@/hooks/useRcaQuery";
import type { ApiError } from "@/api/client";

export const Route = createFileRoute("/rca")({
  head: () => ({
    meta: [
      { title: "Root-Cause Analysis — SETU" },
      {
        name: "description",
        content:
          "Reconstruct equipment failure timelines from work orders and incident reports.",
      },
    ],
  }),
  component: RcaPage,
});

function RcaPage() {
  const mutation = useRcaQuery();
  const [equipmentId, setEquipmentId] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = equipmentId.trim();
    if (!v) return;
    mutation.mutate(v);
  }

  const data = mutation.data;
  const insufficient = data?.insufficient_data;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 md:px-8 md:py-10">
      <PageHeader
        title="Root-cause analysis"
        description="Enter an equipment ID to reconstruct its recent failure history from ingested work orders and incident reports."
      />

      <form
        onSubmit={submit}
        className="mb-8 flex flex-col gap-2 rounded-lg border border-border bg-surface p-3 sm:flex-row"
      >
        <div className="flex flex-1 items-center gap-2 rounded-md border border-border bg-background px-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            value={equipmentId}
            onChange={(e) => setEquipmentId(e.target.value)}
            placeholder="e.g. P204 or C101"
            className="min-h-11 flex-1 bg-transparent font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={!equipmentId.trim() || mutation.isPending}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-40"
        >
          <Wrench className="h-4 w-4" />
          Run analysis
        </button>
      </form>

      {mutation.isPending ? (
        <div className="rounded-lg border border-border bg-surface p-6">
          <LoadingSpinner label="Reconstructing timeline…" />
        </div>
      ) : mutation.error ? (
        <ErrorBanner
          error={mutation.error as ApiError}
          onRetry={() => mutation.mutate(equipmentId.trim())}
        />
      ) : !data ? (
        <EmptyState
          title="No analysis yet"
          description="Enter an equipment ID above to get started."
        />
      ) : insufficient ? (
        <EmptyState
          icon={<ListChecks className="h-5 w-5" />}
          title="Not enough history for this equipment"
          description={
            data.explanation ??
            "No ingested work orders or incident reports reference this equipment yet."
          }
        />
      ) : (
        <div className="space-y-6">
          {data.equipment_id ? (
            <p className="font-mono text-xs uppercase tracking-widest text-primary">
              Equipment · {data.equipment_id}
            </p>
          ) : null}

          {data.failure_summary ? (
            <section className="rounded-lg border border-border bg-surface p-5">
              <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                Failure summary
              </p>
              <p className="text-sm leading-relaxed text-foreground">
                {data.failure_summary}
              </p>
            </section>
          ) : null}

          {data.contributing_factors?.length ? (
            <section className="rounded-lg border border-border bg-surface p-5">
              <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">
                Contributing factors
              </p>
              <ul className="space-y-1.5 text-sm text-foreground">
                {data.contributing_factors.map((f, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    {f}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {data.timeline?.length ? (
            <section>
              <p className="mb-3 text-[11px] uppercase tracking-wide text-muted-foreground">
                Timeline
              </p>
              <Timeline entries={data.timeline} />
            </section>
          ) : null}

          {data.recommendation ? (
            <section className="rounded-lg border border-primary/30 bg-primary/10 p-5">
              <p className="mb-1 text-[11px] uppercase tracking-wide text-primary">
                Recommendation
              </p>
              <p className="text-sm leading-relaxed text-foreground">
                {data.recommendation}
              </p>
            </section>
          ) : null}
        </div>
      )}
    </div>
  );
}
