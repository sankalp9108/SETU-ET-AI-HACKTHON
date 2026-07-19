import { useQuery } from "@tanstack/react-query";
import { getComplianceGaps } from "@/api/compliance";

export function useComplianceGaps() {
  return useQuery({
    queryKey: ["compliance", "gaps"],
    queryFn: getComplianceGaps,
    retry: 0,
    staleTime: 30_000,
  });
}
