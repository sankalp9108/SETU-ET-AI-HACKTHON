import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";
import type { ApiError } from "@/api/client";

export function ErrorBanner({
  error,
  onRetry,
}: {
  error: ApiError | Error | null;
  onRetry?: () => void;
}) {
  if (!error) return null;
  const kind = (error as ApiError).kind;
  const isNetwork = kind === "network";
  const Icon = isNetwork ? WifiOff : AlertTriangle;
  const title = isNetwork
    ? "Cannot reach backend"
    : kind === "server"
      ? "Backend service unavailable"
      : "Something went wrong";

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive-foreground"
    >
      <Icon className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
      <div className="flex-1">
        <p className="font-semibold text-destructive">{title}</p>
        <p className="mt-1 text-foreground/80">{error.message}</p>
      </div>
      {onRetry ? (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 rounded-md border border-destructive/40 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </button>
      ) : null}
    </div>
  );
}
