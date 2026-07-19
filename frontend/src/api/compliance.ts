import { apiClient, parseApiError } from "./client";
import type { ComplianceReport } from "@/types/compliance";

export async function getComplianceGaps(): Promise<ComplianceReport> {
  try {
    const { data } = await apiClient.get<ComplianceReport>("/compliance/gaps");
    return data;
  } catch (err) {
    throw parseApiError(err);
  }
}
