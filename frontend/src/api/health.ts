import { apiClient, parseApiError } from "./client";

export interface HealthResponse {
  status?: string;
  [key: string]: unknown;
}

export async function getHealth(): Promise<HealthResponse> {
  try {
    const { data } = await apiClient.get<HealthResponse>("/health");
    return data;
  } catch (err) {
    throw parseApiError(err);
  }
}
