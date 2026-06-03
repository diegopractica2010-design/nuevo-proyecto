import type { AuthToken, Basket, BasketSummary, CompareResponse, PriceHistoryResponse, ScraperHealthResponse, SearchResponse, StoreId, StoreInfo, UserLoginRequest, UserRegisterRequest, UserResponse } from "@/types/api";

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

// The backend returns errors in two shapes: FastAPI's `{ detail }` (string or
// array) and a custom validation envelope `{ message, details: { fields } }`.
// Pull the most useful human-readable message out of either one.
function extractErrorMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const p = payload as Record<string, unknown>;

  // Custom validation handler: { message, details: { fields: [{ field, message }] } }
  const details = p.details as { fields?: Array<{ message?: string }> } | undefined;
  if (details?.fields?.length) {
    const msgs = details.fields.map((f) => f.message).filter(Boolean);
    if (msgs.length) return msgs.join(" · ");
  }

  // FastAPI default: detail can be a string or an array of { msg }
  if (typeof p.detail === "string") return p.detail;
  if (Array.isArray(p.detail)) {
    const msgs = p.detail.map((d) => (d as { msg?: string })?.msg).filter(Boolean);
    if (msgs.length) return msgs.join(" · ");
  }

  if (typeof p.message === "string") return p.message;
  return null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      ...getAuthHeader(),
      ...init?.headers
    }
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(extractErrorMessage(payload) ?? `Request failed with ${response.status}`);
  }

  // 204 No Content or empty body — skip JSON parsing
  const contentLength = response.headers.get("content-length");
  if (response.status === 204 || contentLength === "0") {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  searchProducts({ query, store, limit = 12 }: SearchParams) {
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
  },

  getBaskets(limit = 20, offset = 0) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return request<{ items: BasketSummary[]; total: number; limit: number; offset: number; has_more: boolean }>(`/baskets?${params.toString()}`);
  },

  getBasket(basketId: string) {
    return request<Basket>(`/baskets/${basketId}`);
  },

  createBasket(name: string) {
    return request<Basket>("/baskets", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  addToBasket(basketId: string, product: Record<string, unknown>, quantity = 1) {
    return request<{ message: string }>(`/baskets/${basketId}/items`, {
      method: "POST",
      body: JSON.stringify({ product, quantity }),
    });
  },

  updateBasketItem(basketId: string, productId: string, quantity: number) {
    return request<{ message: string }>(`/baskets/${basketId}/items/${productId}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity }),
    });
  },

  logout() {
    return request<{ detail: string }>("/auth/logout", { method: "POST" });
  },

  getBackupStatus() {
    return request<{ last_backup: string | null; status: string }>("/admin/backup-status");
  },

  triggerBackup() {
    return request<{ detail: string }>("/admin/backup", { method: "POST" });
  },

  promoteUser(username: string, role: string) {
    return request<{ detail: string }>("/admin/promote", {
      method: "POST",
      body: JSON.stringify({ username, role }),
    });
  },

  forceParserCheck() {
    return request<{ detail: string }>("/monitoring/parser-check", { method: "POST" });
  },

  deleteBasket(basketId: string) {
    return request<void>(`/baskets/${basketId}`, { method: "DELETE" });
  },

  deleteBasketItem(basketId: string, productId: string) {
    return request<void>(`/baskets/${basketId}/items/${productId}`, { method: "DELETE" });
  },

  forgotPassword(email: string) {
    return request<{ detail: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  resetPassword(token: string, newPassword: string) {
    return request<{ detail: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  },
};
