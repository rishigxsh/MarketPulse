import { useState, useEffect } from "react";
import { useLatestPrices } from "../hooks/usePrices";

interface Props {
  onSelectSymbol: (symbol: string) => void;
  selectedSymbol: string;
}

const STORAGE_KEY = "marketpulse:watchlist";

function loadWatchlist(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export default function Watchlist({ onSelectSymbol, selectedSymbol }: Props) {
  const [watchlist, setWatchlist] = useState<string[]>(loadWatchlist);
  const [search, setSearch] = useState("");
  const { data: coins } = useLatestPrices();

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist));
  }, [watchlist]);

  const coinMap = new Map((coins ?? []).map((c) => [c.symbol, c]));

  const toggle = (symbol: string) => {
    setWatchlist((prev) =>
      prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol],
    );
  };

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <h2 className="text-sm font-medium uppercase tracking-wider text-gray-400 mb-3">
        Watchlist
      </h2>

      {watchlist.length === 0 ? (
        <p className="text-xs text-gray-600">Click a coin card to add it here.</p>
      ) : (
        <ul className="space-y-2">
          {watchlist.map((sym) => {
            const coin = coinMap.get(sym);
            return (
              <li key={sym} className="flex items-center justify-between">
                <button
                  onClick={() => onSelectSymbol(sym)}
                  className={`text-sm font-medium cursor-pointer ${
                    sym === selectedSymbol ? "text-indigo-400" : "text-white hover:text-indigo-300"
                  }`}
                >
                  {sym.toUpperCase()}
                  {coin && (
                    <span className="text-gray-500 ml-2">
                      ${coin.price_usd >= 1 ? coin.price_usd.toLocaleString() : coin.price_usd.toPrecision(4)}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => toggle(sym)}
                  className="text-gray-600 hover:text-red-400 text-xs cursor-pointer"
                  aria-label={`Remove ${sym} from watchlist`}
                >
                  ✕
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {coins && coins.length > 0 && (
        <div className="mt-4">
          <input
            type="text"
            placeholder="Search coins..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 mb-2"
          />
          {search.trim() && <div className="max-h-48 overflow-y-auto space-y-1">
            {coins
              .filter((c) => !watchlist.includes(c.symbol))
              .filter((c) => {
                const q = search.toLowerCase();
                return c.symbol.toLowerCase().includes(q) || c.name.toLowerCase().includes(q);
              })
              .map((c) => (
                <button
                  key={c.symbol}
                  onClick={() => { toggle(c.symbol); setSearch(""); }}
                  className="block w-full text-left text-xs text-gray-400 hover:text-white py-1 cursor-pointer"
                >
                  + {c.symbol.toUpperCase()} — {c.name}
                </button>
              ))}
          </div>}
        </div>
      )}
    </div>
  );
}
