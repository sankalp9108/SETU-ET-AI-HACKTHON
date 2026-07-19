import { useMutation } from "@tanstack/react-query";
import { postLessonsCheck } from "@/api/lessons";

export function useLessonsCheck() {
  return useMutation({
    mutationFn: (description: string) => postLessonsCheck(description),
  });
}
