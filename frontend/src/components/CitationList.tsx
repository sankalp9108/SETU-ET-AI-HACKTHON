import { FileText } from "lucide-react";

export function CitationList({ citations }: { citations: string[] }) {
  if (!citations?.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {citations.map((c, i) => (
        <span
          key={`${c}-${i}`}
          className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-1 font-mono text-xs text-muted-foreground"
        >
          <FileText className="h-3 w-3" />
          {c}
        </span>
      ))}
    </div>
  );
}
