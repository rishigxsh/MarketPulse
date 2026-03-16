import axios from "axios";
import type { APIResponse, StockPrice } from "../types";

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "" });

export async function fetchLatestStocks(): Promise<StockPrice[]> {
  const { data } = await api.get<APIResponse<StockPrice[]>>("/stocks/latest");
  return data.data ?? [];
}

export async function fetchStockHistory(
  symbol: string,
  from: string,
  to: string,
  interval?: string,
): Promise<StockPrice[]> {
  const params: Record<string, string> = { from, to };
  if (interval) params.interval = interval;
  const { data } = await api.get<APIResponse<StockPrice[]>>(`/stocks/${symbol}/history`, { params });
  return data.data ?? [];
}
