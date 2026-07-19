import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Lightbulb, FileText } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { useLessonsCheck } from "@/hooks/useLessonsCheck";
import type { ApiError } from "@/api/client";
import type { LessonsLearnedAlert } from "@/types/lessons";

export const Route = createFileRoute("/lessons")({
  head: () => ({
    meta: [
      { title: "Lessons Learned — SETU" },
      {
        name: "description",
        content:
          "Compare a new incident against past reports to surface similar events and shared equipment.",
      },
    ],
  }),
  component: LessonsPage,
});

function LessonsPage() {
  const mutation = useLessonsCheck();
  const [text, setText] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = text.trim();
    if (!v) return;
    mutation.mutate(v);
  }

  const data = mutation.data;
  const insufficient = data?.insufficient_data;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 md:px-8 md:py-10">
      <PageHeader
        title="Lessons learned"
        description="Describe a new incident. We'll check it against past incident reports for similar events and shared equipment."
      />

      <form
        onSubmit={submit}
        className="mb-8 rounded-lg border border-border bg-surface p-3"
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder="Describe what happened, when, and which equipment was involved…"
          className="w-full resize-y rounded-md border border-border bg-background p-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <div className="mt-3 flex justify-end">
          <button
            type="submit"
            disabled={!text.trim() || mutation.isPending}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-40"
          >
            <Lightbulb className="h-4 w-4" />
            Check for similar incidents
          </button>
        </div>
      </form>

      {mutation.isPending ? (
        <div className="rounded-lg border border-border bg-surface p-6">
          <LoadingSpinner label="Searching past incidents…" />
        </div>
      ) : mutation.error ? (
        <ErrorBanner
          error={mutation.error as ApiError}
          onRetry={() => mutation.mutate(text.trim())}
        />
      ) : !data ? (
        <EmptyState
          title="Nothing checked yet"
          description="Paste an incident description above to look for similar past events."
        />
      ) : insufficient ? (
        <EmptyState
          icon={<FileText className="h-5 w-5" />}
          title="Not enough past incidents to compare against"
          description={
            data.explanation ??
            "Ingest at least one incident report before running this check."
          }
        />
      ) : !data.alerts.length ? (
        <EmptyState
          icon={<Lightbulb className="h-5 w-5" />}
          title="No similar incidents found"
          description="This description doesn't match any past incident report in the knowledge base."
        />
      ) : (
        <div className="space-y-3">
          {data.alerts.map((a, i) => (
            <AlertCard key={`${a.filename}-${i}`} alert={a} />
          ))}
        </div>
      )}
    </div>
  );
}

function AlertCard({ alert }: { alert: LessonsLearnedAlert }) {
  const pct = Math.round(alert.similarity * 100);
  return (
    <article className="rounded-lg border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          <FileText className="h-4 w-4 text-primary" />
          <span className="font-mono text-xs text-muted-foreground">
            {alert.filename}
          </span>
        </div>
        <div className="flex w-40 items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">{pct}%</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-primary"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-foreground">
        {alert.excerpt}
      </p>

      {alert.shared_equipment_ids.length ? (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Shared equipment
          </span>
          {alert.shared_equipment_ids.map((id) => (
            <span
              key={id}
              className="rounded-md border border-primary/40 bg-primary/10 px-2 py-0.5 font-mono text-xs text-primary"
            >
              {id}
            </span>
          ))}
        </div>
      ) : null}

      {alert.note ? (
        <p className="mt-3 rounded-md border border-border bg-background px-3 py-2 text-xs text-muted-foreground">
          {alert.note}
        </p>
      ) : null}
    </article>
  );
}
