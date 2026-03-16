export interface APIResponse<T> {
  data: T | null;
  error: string | null;
  timestamp: string;
}

export interface CryptoPrice {
  symbol: string;
  name: string;
  price_usd: number;
  market_cap: number | null;
  volume_24h: number | null;
  price_change_24h: number | null;
  timestamp: string;
}

export interface StockPrice {
  symbol: string;
  name: string;
  price_usd: number;
  market_cap: number | null;
  volume_24h: number | null;
  price_change_24h: number | null;
  timestamp: string;
}

export interface PriceAlert {
  id: number;
  symbol: string;
  target_price: number;
  direction: "above" | "below";
  triggered: boolean;
  created_at: string;
  triggered_at: string | null;
}

export interface CreateAlertPayload {
  symbol: string;
  target_price: number;
  direction: "above" | "below";
}
