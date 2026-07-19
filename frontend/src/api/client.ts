import axios, { AxiosError } from "axios";

const baseURL =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE_URL) ||
  "http://localhost:8000";

export const apiClient = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
  timeout: 60_000,
});

export type ApiErrorKind = "network" | "validation" | "server" | "unknown";

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number;
  detail: string;

  constructor(message: string, kind: ApiErrorKind, status?: number) {
    super(message);
    this.kind = kind;
    this.status = status;
    this.detail = message;
  }
}

interface FastAPIValidationItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export function parseApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const ax = err as AxiosError<unknown>;
    if (!ax.response) {
      return new ApiError(
        "Cannot reach the backend. Check that the API is running and reachable.",
        "network",
      );
    }
    const status = ax.response.status;
    const data = ax.response.data as
      | { detail?: string | FastAPIValidationItem[] }
      | undefined;

    if (status === 422 && Array.isArray(data?.detail)) {
      const first = data!.detail![0];
      const path = first.loc.slice(1).join(".") || "input";
      return new ApiError(`${path}: ${first.msg}`, "validation", 422);
    }
    if (typeof data?.detail === "string") {
      return new ApiError(data.detail, status >= 500 ? "server" : "unknown", status);
    }
    return new ApiError(
      `Request failed with status ${status}.`,
      status >= 500 ? "server" : "unknown",
      status,
    );
  }
  if (err instanceof Error) return new ApiError(err.message, "unknown");
  return new ApiError("Unknown error", "unknown");
}
