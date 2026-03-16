import { useState } from "react";
import PriceGrid from "../components/PriceGrid";
import PriceChart from "../components/PriceChart";
import StockGrid from "../components/StockGrid";
import StockChart from "../components/StockChart";
import Watchlist from "../components/Watchlist";
import AlertsPanel from "../components/AlertsPanel";

type Tab = "crypto" | "stocks";

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("crypto");
  const [cryptoSymbol, setCryptoSymbol] = useState("btc");
  const [stockSymbol, setStockSymbol] = useState("aapl");

  const selectedSymbol = tab === "crypto" ? cryptoSymbol : stockSymbol;
  const onSelectSymbol = tab === "crypto" ? setCryptoSymbol : setStockSymbol;

  return (
    <div className="space-y-6">
      {/* Tab switcher */}
      <div className="flex gap-1 bg-gray-900 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab("crypto")}
          className={`px-5 py-2 text-sm font-medium rounded-md transition-colors cursor-pointer ${
            tab === "crypto"
              ? "bg-indigo-600 text-white"
              : "text-gray-400 hover:text-white"
          }`}
        >
          Crypto
        </button>
        <button
          onClick={() => setTab("stocks")}
          className={`px-5 py-2 text-sm font-medium rounded-md transition-colors cursor-pointer ${
            tab === "stocks"
              ? "bg-emerald-600 text-white"
              : "text-gray-400 hover:text-white"
          }`}
        >
          Stocks
        </button>
      </div>

      {/* Chart + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 flex">
          {tab === "crypto" ? (
            <PriceChart symbol={cryptoSymbol} />
          ) : (
            <StockChart symbol={stockSymbol} />
          )}
        </div>
        <div className="space-y-6">
          <Watchlist
            selectedSymbol={selectedSymbol}
            onSelectSymbol={onSelectSymbol}
          />
          <AlertsPanel />
        </div>
      </div>

      {/* Price grid */}
      {tab === "crypto" ? (
        <PriceGrid selectedSymbol={cryptoSymbol} onSelectSymbol={setCryptoSymbol} />
      ) : (
        <StockGrid selectedSymbol={stockSymbol} onSelectSymbol={setStockSymbol} />
      )}
    </div>
  );
}
