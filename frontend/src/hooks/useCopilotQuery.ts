import { useMutation } from "@tanstack/react-query";
import { postCopilotQuery } from "@/api/copilot";

export function useCopilotQuery() {
  return useMutation({
    mutationFn: (question: string) => postCopilotQuery(question),
  });
}
