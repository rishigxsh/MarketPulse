import { useState } from "react";
import { useAlerts, useCreateAlert, useDeleteAlert } from "../hooks/useAlerts";
import type { CreateAlertPayload } from "../types";

export default function AlertsPanel() {
  const { data: alerts, isLoading } = useAlerts();
  const createMutation = useCreateAlert();
  const deleteMutation = useDeleteAlert();

  const [symbol, setSymbol] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [direction, setDirection] = useState<"above" | "below">("above");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim() || !targetPrice) return;

    const payload: CreateAlertPayload = {
      symbol: symbol.trim().toLowerCase(),
      target_price: parseFloat(targetPrice),
      direction,
    };
    createMutation.mutate(payload, {
      onSuccess: () => {
        setSymbol("");
        setTargetPrice("");
      },
    });
  };

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <h2 className="text-sm font-medium uppercase tracking-wider text-gray-400 mb-3">
        Price Alerts
      </h2>

      <form onSubmit={handleSubmit} className="flex flex-col gap-2 mb-4">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Symbol (e.g. btc)"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="flex-1 rounded-md bg-gray-800 border border-gray-700 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
          <input
            type="number"
            step="any"
            placeholder="Price"
            value={targetPrice}
            onChange={(e) => setTargetPrice(e.target.value)}
            className="w-28 rounded-md bg-gray-800 border border-gray-700 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex gap-2">
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as "above" | "below")}
            className="flex-1 rounded-md bg-gray-800 border border-gray-700 px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="above">Above</option>
            <option value="below">Below</option>
          </select>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="px-4 py-1.5 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 cursor-pointer"
          >
            {createMutation.isPending ? "..." : "Create"}
          </button>
        </div>
      </form>

      {isLoading ? (
        <p className="text-xs text-gray-600">Loading alerts...</p>
      ) : !alerts || alerts.length === 0 ? (
        <p className="text-xs text-gray-600">No alerts yet.</p>
      ) : (
        <ul className="space-y-2 max-h-64 overflow-y-auto">
          {alerts.map((alert) => (
            <li
              key={alert.id}
              className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm ${
                alert.triggered
                  ? "border border-amber-600/50 bg-amber-950/30"
                  : "bg-gray-800/50"
              }`}
            >
              <div>
                <span className="font-medium text-white uppercase">{alert.symbol}</span>
                <span className="text-gray-400 ml-2">
                  {alert.direction} ${alert.target_price.toLocaleString()}
                </span>
                {alert.triggered && (
                  <span className="ml-2 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-amber-600 text-black">
                    Triggered
                  </span>
                )}
              </div>
              <button
                onClick={() => deleteMutation.mutate(alert.id)}
                className="text-gray-600 hover:text-red-400 text-xs cursor-pointer"
                aria-label="Delete alert"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
