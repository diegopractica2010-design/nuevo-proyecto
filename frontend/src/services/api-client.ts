import type { CompareResponse, ScraperHealthResponse, SearchResponse, StoreId } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

interface SearchParams {
  query: string;
  store: StoreId;
  limit?: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
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
  }
};
