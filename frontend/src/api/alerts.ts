import axios from "axios";
import type { APIResponse, PriceAlert, CreateAlertPayload } from "../types";

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "" });

export async function fetchAlerts(): Promise<PriceAlert[]> {
  const { data } = await api.get<APIResponse<PriceAlert[]>>("/alerts");
  return data.data ?? [];
}

export async function createAlert(payload: CreateAlertPayload): Promise<PriceAlert> {
  const { data } = await api.post<APIResponse<PriceAlert>>("/alerts", payload);
  return data.data!;
}

export async function deleteAlert(id: number): Promise<void> {
  await api.delete(`/alerts/${id}`);
}
