import { useQuery } from "@tanstack/react-query";
import { fetchLatestPrices } from "../api/prices";

export function useLatestPrices() {
  return useQuery({
    queryKey: ["prices", "latest"],
    queryFn: fetchLatestPrices,
    refetchInterval: 30_000,
  });
}
