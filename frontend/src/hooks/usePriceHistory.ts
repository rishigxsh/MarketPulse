import { useQuery } from "@tanstack/react-query";
import { fetchPriceHistory } from "../api/prices";

export function usePriceHistory(symbol: string, from: string, to: string, interval?: string) {
  return useQuery({
    queryKey: ["prices", "history", symbol, from, to, interval],
    queryFn: () => fetchPriceHistory(symbol, from, to, interval),
    enabled: !!symbol,
  });
}
