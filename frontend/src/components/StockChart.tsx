import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useStockHistory } from "../hooks/useStocks";

interface Props {
  symbol: string;
}

const RANGES = [
  { label: "24h", hours: 24, interval: "1h" },
  { label: "7d", hours: 168, interval: "1h" },
  { label: "30d", hours: 720, interval: "1d" },
] as const;

export default function StockChart({ symbol }: Props) {
  const [rangeIdx, setRangeIdx] = useState(0);
  const range = RANGES[rangeIdx];

  const to = useMemo(() => new Date().toISOString(), [rangeIdx]);
  const from = useMemo(
    () => new Date(Date.now() - range.hours * 3600_000).toISOString(),
    [rangeIdx, range.hours],
  );

  const { data, isLoading, error } = useStockHistory(symbol, from, to, range.interval);

  const chartData = useMemo(
    () =>
      (data ?? []).map((p) => ({
        time: new Date(p.timestamp).getTime(),
        price: p.price_usd,
      })),
    [data],
  );

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    if (range.hours <= 24) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (range.hours <= 168) return d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit" });
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4 w-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-gray-400">
          {symbol.toUpperCase()} Price History
        </h2>
        <div className="flex gap-1">
          {RANGES.map((r, i) => (
            <button
              key={r.label}
              onClick={() => setRangeIdx(i)}
              className={`px-3 py-1 text-xs rounded-md transition-colors cursor-pointer ${
                i === rangeIdx
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <p className="text-red-400 text-sm py-8 text-center">Failed to load chart data.</p>
      ) : isLoading ? (
        <div className="h-96 flex items-center justify-center text-gray-600 text-sm">
          Loading chart...
        </div>
      ) : chartData.length === 0 ? (
        <div className="h-96 flex items-center justify-center text-gray-600 text-sm">
          No data for this range yet.
        </div>
      ) : (
        <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="time"
              tickFormatter={formatTime}
              stroke="#6b7280"
              tick={{ fontSize: 11 }}
              minTickGap={40}
            />
            <YAxis
              domain={["auto", "auto"]}
              stroke="#6b7280"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `$${v.toLocaleString()}`}
              width={80}
            />
            <Tooltip
              contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 8 }}
              labelFormatter={(ts) => new Date(Number(ts)).toLocaleString()}
              formatter={(value) => [`$${Number(value).toLocaleString()}`, "Price"]}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              animationDuration={300}
            />
          </LineChart>
        </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
