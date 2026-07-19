import { apiClient, parseApiError } from "./client";
import type { RCAQueryResponse } from "@/types/rca";

export async function postRcaQuery(
  equipmentId: string,
): Promise<RCAQueryResponse> {
  try {
    const { data } = await apiClient.post<RCAQueryResponse>("/rca/query", {
      equipment_id: equipmentId,
    });
    return data;
  } catch (err) {
    throw parseApiError(err);
  }
}
