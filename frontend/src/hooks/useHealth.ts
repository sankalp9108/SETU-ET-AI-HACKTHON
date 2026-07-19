import { useQuery } from "@tanstack/react-query";
import { getHealth } from "@/api/health";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 15_000,
    retry: 0,
    staleTime: 10_000,
  });
}
