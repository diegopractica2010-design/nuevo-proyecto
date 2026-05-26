import type { AuthToken, CompareResponse, PriceHistoryResponse, ScraperHealthResponse, SearchResponse, StoreId, StoreInfo, UserLoginRequest, UserRegisterRequest, UserResponse } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

interface SearchParams {
  query: string;
  store: StoreId;
  limit?: number;
}

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
      ...init?.headers
    }
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  searchProducts({ query, store, limit = 48 }: SearchParams) {
    const params = new URLSearchParams({ q: query, store, limit: String(limit) });
    return request<SearchResponse>(`/search?${params.toString()}`);
  },

  compareShoppingList(items: string[]) {
    return request<CompareResponse>("/shopping-list/compare", {
      method: "POST",
      body: JSON.stringify({ items })
    });
  },

  getScraperHealth() {
    return request<ScraperHealthResponse>("/health/scraper", {
      cache: "no-store"
    });
  },

  login(body: UserLoginRequest) {
    return request<AuthToken>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body)
    });
  },

  register(body: UserRegisterRequest) {
    return request<UserResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body)
    });
  },

  getMe() {
    return request<UserResponse>("/auth/me");
  },

  getPriceHistory(product_id: string, store: StoreId) {
    const params = new URLSearchParams({ store });
    return request<PriceHistoryResponse>(`/price-history/${encodeURIComponent(product_id)}?${params.toString()}`);
  },

  getStores() {
    return request<StoreInfo[]>("/stores");
  }
};
