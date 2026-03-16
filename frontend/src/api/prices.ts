import axios from "axios";
import type { APIResponse, CryptoPrice } from "../types";

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "" });

export async function fetchLatestPrices(): Promise<CryptoPrice[]> {
  const { data } = await api.get<APIResponse<CryptoPrice[]>>("/prices/latest");
  return data.data ?? [];
}

export async function fetchPriceHistory(
  symbol: string,
  from: string,
  to: string,
  interval?: string,
): Promise<CryptoPrice[]> {
  const params: Record<string, string> = { from, to };
  if (interval) params.interval = interval;
  const { data } = await api.get<APIResponse<CryptoPrice[]>>(`/prices/${symbol}/history`, { params });
  return data.data ?? [];
}
