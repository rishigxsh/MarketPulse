import { useLatestPrices } from "../hooks/usePrices";
import PriceCard from "./PriceCard";
import SkeletonCard from "./SkeletonCard";

interface Props {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}

export default function PriceGrid({ selectedSymbol, onSelectSymbol }: Props) {
  const { data: coins, isLoading, error } = useLatestPrices();

  if (error) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/30 p-4 text-red-400 text-sm">
        Failed to load prices. Is the backend running?
      </div>
    );
  }

  if (isLoading || !coins) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {Array.from({ length: 20 }, (_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {coins.map((coin) => (
        <PriceCard
          key={coin.symbol}
          coin={coin}
          selected={coin.symbol === selectedSymbol}
          onSelect={onSelectSymbol}
        />
      ))}
    </div>
  );
}
