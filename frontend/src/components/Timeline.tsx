import { FileText, AlertCircle, Wrench } from "lucide-react";
import type { RCATimelineEntry } from "@/types/rca";

function iconFor(eventType: string) {
  const t = eventType.toLowerCase();
  if (t.includes("incident")) return AlertCircle;
  if (t.includes("work")) return Wrench;
  return FileText;
}

export function Timeline({ entries }: { entries: RCATimelineEntry[] }) {
  if (!entries.length) return null;
  return (
    <ol className="relative space-y-4 border-l border-border pl-6">
      {entries.map((e, i) => {
        const Icon = iconFor(e.event_type);
        return (
          <li key={`${e.date}-${i}`} className="relative">
            <span className="absolute -left-[33px] flex h-6 w-6 items-center justify-center rounded-full border border-border bg-surface text-primary">
              <Icon className="h-3.5 w-3.5" />
            </span>
            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-primary">
                  {e.event_type.replace(/_/g, " ")}
                </span>
                <time className="font-mono text-xs text-muted-foreground">
                  {e.date}
                </time>
              </div>
              <p className="mt-2 text-sm text-foreground">{e.description}</p>
              <p className="mt-2 inline-flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
                <FileText className="h-3 w-3" />
                {e.source_document}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
