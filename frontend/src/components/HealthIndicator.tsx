import { useHealth } from "@/hooks/useHealth";

export function HealthIndicator() {
  const { data, isError, isLoading } = useHealth();
  const online = !isError && !!data;
  const label = isLoading ? "Checking…" : online ? "Backend online" : "Offline";
  const dot = isLoading
    ? "bg-muted-foreground"
    : online
      ? "bg-success"
      : "bg-destructive";
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/60 px-2.5 py-1 text-xs text-muted-foreground">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {label}
    </span>
  );
}
