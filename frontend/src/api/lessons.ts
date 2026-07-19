import { apiClient, parseApiError } from "./client";
import type { LessonsLearnedReport } from "@/types/lessons";

export async function postLessonsCheck(
  description: string,
): Promise<LessonsLearnedReport> {
  try {
    const { data } = await apiClient.post<LessonsLearnedReport>(
      "/lessons/check",
      { description },
    );
    return data;
  } catch (err) {
    throw parseApiError(err);
  }
}
