import { apiClient, parseApiError } from "./client";
import type { CopilotQueryResponse } from "@/types/copilot";

export async function postCopilotQuery(
  question: string,
): Promise<CopilotQueryResponse> {
  try {
    const { data } = await apiClient.post<CopilotQueryResponse>(
      "/copilot/query",
      { question },
    );
    return data;
  } catch (err) {
    throw parseApiError(err);
  }
}
