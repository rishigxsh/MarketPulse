import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchAlerts, createAlert, deleteAlert } from "../api/alerts";
import type { CreateAlertPayload } from "../types";

export function useAlerts() {
  return useQuery({
    queryKey: ["alerts"],
    queryFn: fetchAlerts,
    refetchInterval: 30_000,
  });
}

export function useCreateAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateAlertPayload) => createAlert(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
}

export function useDeleteAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteAlert(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
}
