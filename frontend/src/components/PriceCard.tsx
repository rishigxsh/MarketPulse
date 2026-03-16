import type { CryptoPrice } from "../types";

interface Props {
  coin: CryptoPrice;
  selected: boolean;
  onSelect: (symbol: string) => void;
}

function formatPrice(n: number): string {
  if (n >= 1) return n.toLocaleString("en-US", { style: "currency", currency: "USD" });
  return "$" + n.toPrecision(4);
}

function formatMarketCap(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

export default function PriceCard({ coin, selected, onSelect }: Props) {
  const change = coin.price_change_24h;
  const changeColor =
    change == null ? "text-gray-500" : change >= 0 ? "text-green-400" : "text-red-400";
  const changeText =
    change == null ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;

  return (
    <button
      onClick={() => onSelect(coin.symbol)}
      className={`w-full text-left rounded-xl border p-4 transition-colors cursor-pointer ${
        selected
          ? "border-indigo-500 bg-indigo-950/40"
          : "border-gray-800 bg-gray-900 hover:border-gray-700"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium uppercase tracking-wider text-gray-400">
          {coin.symbol}
        </span>
        <span className={`text-xs font-medium ${changeColor}`}>{changeText}</span>
      </div>
      <p className="text-lg font-semibold text-white">{formatPrice(coin.price_usd)}</p>
      <p className="text-xs text-gray-500 mt-1">MCap {formatMarketCap(coin.market_cap)}</p>
    </button>
  );
}
