import { useQuery } from "@tanstack/react-query";
import { fetchLatestStocks, fetchStockHistory } from "../api/stocks";

export function useLatestStocks() {
  return useQuery({
    queryKey: ["stocks", "latest"],
    queryFn: fetchLatestStocks,
    refetchInterval: 30_000,
  });
}

export function useStockHistory(symbol: string, from: string, to: string, interval?: string) {
  return useQuery({
    queryKey: ["stocks", "history", symbol, from, to, interval],
    queryFn: () => fetchStockHistory(symbol, from, to, interval),
    enabled: !!symbol,
  });
}
