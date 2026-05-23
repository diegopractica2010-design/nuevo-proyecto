export type StoreId = "lider" | "jumbo";

export interface Product {
  id?: string | null;
  sku?: string | null;
  name: string;
  brand?: string | null;
  category?: string | null;
  price: number;
  original_price?: number | null;
  discount_percent?: number | null;
  savings_amount?: number | null;
  savings_text?: string | null;
  unit_price?: string | null;
  image?: string | null;
  url?: string | null;
  availability?: string | null;
  in_stock: boolean;
  seller?: string | null;
  badges: string[];
  is_offer: boolean;
  position?: number | null;
  currency: string;
  source: StoreId | string;
}

export interface FacetValue {
  name: string;
  count: number;
}

export interface SearchResponse {
  query: string;
  applied_query?: string | null;
  count: number;
  results: Product[];
  facets: {
    brands: FacetValue[];
    categories: FacetValue[];
    price_range: { min?: number | null; max?: number | null };
  };
  stats: {
    min_price?: number | null;
    max_price?: number | null;
    average_price?: number | null;
    offer_count: number;
    in_stock_count: number;
  };
  suggestions: string[];
  fetched_at?: string | null;
  source: StoreId | string;
  source_url?: string | null;
  strategy?: string | null;
  cached: boolean;
  warning?: string | null;
}

export interface CompareStoreResult {
  store: StoreId;
  count: number;
  matched_count: number;
  best: Product | null;
  alternatives: Product[];
  warning?: string | null;
  applied_query?: string | null;
  error?: string;
}

export interface CompareItemResult {
  query: string;
  quantity: number;
  stores: CompareStoreResult[];
  cheapest: Product | null;
  same_product: boolean;
  status: "matched" | "not_found";
}

export interface CompareResponse {
  items: CompareItemResult[];
  count: number;
  matched_count: number;
  estimated_total: number;
}

export interface ScraperHealthStore {
  status: "ok" | "degraded" | "down" | string;
  timestamp?: string;
  duration_seconds?: number;
  product_count?: number;
  parse_strategy?: string;
  first_price?: number | null;
  issues?: string[];
  structure_changed?: boolean;
  structure_detail?: string;
}

export interface ScraperHealthResponse {
  status: "ok" | "degraded" | "down" | "unknown" | string;
  last_check?: string | null;
  stores: Record<string, ScraperHealthStore>;
}
