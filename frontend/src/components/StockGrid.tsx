import { useLatestStocks } from "../hooks/useStocks";
import PriceCard from "./PriceCard";
import SkeletonCard from "./SkeletonCard";

interface Props {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}

export default function StockGrid({ selectedSymbol, onSelectSymbol }: Props) {
  const { data: stocks, isLoading, error } = useLatestStocks();

  if (error) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/30 p-4 text-red-400 text-sm">
        Failed to load stocks. Is the backend running with Finnhub configured?
      </div>
    );
  }

  if (isLoading || !stocks) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {Array.from({ length: 10 }, (_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (stocks.length === 0) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 text-gray-500 text-sm text-center">
        No stock data yet. Add a FINNHUB_API_KEY to your .env to enable stock ingestion.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {stocks.map((stock) => (
        <PriceCard
          key={stock.symbol}
          coin={stock}
          selected={stock.symbol === selectedSymbol}
          onSelect={onSelectSymbol}
        />
      ))}
    </div>
  );
}
