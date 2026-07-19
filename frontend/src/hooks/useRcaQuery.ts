import { useMutation } from "@tanstack/react-query";
import { postRcaQuery } from "@/api/rca";

export function useRcaQuery() {
  return useMutation({
    mutationFn: (equipmentId: string) => postRcaQuery(equipmentId),
  });
}
