import { cn } from "@/lib/utils";
import type { Severity } from "@/types/compliance";

const styles: Record<Severity, string> = {
  CRITICAL: "bg-destructive/15 text-destructive border-destructive/40",
  HIGH: "bg-warning/15 text-warning border-warning/40",
  MEDIUM: "bg-caution/15 text-caution border-caution/40",
  LOW: "bg-muted text-muted-foreground border-border",
};

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide uppercase",
        styles[severity] ?? styles.LOW,
        className,
      )}
    >
      {severity}
    </span>
  );
}
