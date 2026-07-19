import { createFileRoute } from "@tanstack/react-router";
import { ShieldCheck, ShieldAlert, FileText } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { SeverityBadge } from "@/components/SeverityBadge";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { SkeletonBlock } from "@/components/LoadingSpinner";
import { useComplianceGaps } from "@/hooks/useComplianceGaps";
import type { ApiError } from "@/api/client";
import type { ComplianceGap, Severity } from "@/types/compliance";

export const Route = createFileRoute("/compliance")({
  head: () => ({
    meta: [
      { title: "Compliance Gaps — SETU" },
      {
        name: "description",
        content:
          "Automated compliance gap analysis of plant documents against regulatory references.",
      },
    ],
  }),
  component: CompliancePage,
});

const ORDER: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

function CompliancePage() {
  const { data, error, isLoading, refetch, isFetching } = useComplianceGaps();

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 md:px-8 md:py-10">
      <PageHeader
        title="Compliance gaps"
        description="Findings extracted from ingested plant documents, checked against your regulatory references."
        actions={
          data ? (
            <div className="flex gap-2 text-xs">
              <StatChip label="Documents checked" value={data.documents_checked} />
              <StatChip
                label="Regulatory sources"
                value={data.regulatory_documents_used}
              />
            </div>
          ) : null
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonBlock key={i} className="h-24" />
          ))}
        </div>
      ) : error ? (
        <ErrorBanner error={error as ApiError} onRetry={() => refetch()} />
      ) : data?.insufficient_data ? (
        <EmptyState
          icon={<FileText className="h-5 w-5" />}
          title="Not enough documents ingested"
          description={
            data.explanation ??
            "Ingest plant SOPs and regulatory references, then re-run the gap analysis."
          }
        />
      ) : !data?.gaps.length ? (
        <EmptyState
          icon={<ShieldCheck className="h-5 w-5" />}
          title="No compliance gaps found"
          description="Every checked document aligns with the loaded regulatory references."
        />
      ) : (
        <div className="space-y-6">
          {ORDER.filter((s) => data.gaps.some((g) => g.severity === s)).map(
            (sev) => (
              <section key={sev} className="space-y-3">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={sev} />
                  <span className="text-xs text-muted-foreground">
                    {data.gaps.filter((g) => g.severity === sev).length} finding
                    {data.gaps.filter((g) => g.severity === sev).length === 1
                      ? ""
                      : "s"}
                  </span>
                </div>
                <div className="space-y-3">
                  {data.gaps
                    .filter((g) => g.severity === sev)
                    .map((g, i) => (
                      <GapCard key={`${g.document_filename}-${i}`} gap={g} />
                    ))}
                </div>
              </section>
            ),
          )}
          {isFetching ? (
            <p className="text-xs text-muted-foreground">Refreshing…</p>
          ) : null}
        </div>
      )}
    </div>
  );
}

function StatChip({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="font-mono text-sm font-semibold">{value}</p>
    </div>
  );
}

function GapCard({ gap }: { gap: ComplianceGap }) {
  return (
    <article className="rounded-lg border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          <ShieldAlert className="h-4 w-4 text-primary" />
          <span className="font-mono text-xs text-muted-foreground">
            {gap.document_filename}
          </span>
        </div>
        <SeverityBadge severity={gap.severity} />
      </div>
      <p className="mt-3 text-sm font-medium text-foreground">
        {gap.description}
      </p>
      <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
            Evidence
          </p>
          <p className="text-foreground/90">{gap.evidence}</p>
        </div>
        <div>
          <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
            Regulation
          </p>
          <p className="text-foreground/90">
            {gap.regulation_reference ?? (
              <span className="italic text-muted-foreground">
                No matching regulatory document
              </span>
            )}
          </p>
        </div>
      </div>
    </article>
  );
}
