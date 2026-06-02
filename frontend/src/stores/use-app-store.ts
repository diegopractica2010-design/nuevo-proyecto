import { create } from "zustand";
import type { Product, StoreId } from "@/types/api";

interface CartItem {
  product: Product;
  quantity: number;
}

interface AppState {
  activeStore: StoreId;
  recentQueries: string[];
  favoriteProductIds: string[];
  authToken: string | null;
  authUsername: string | null;
  cart: CartItem[];
  cartCount: number;
  setActiveStore: (store: StoreId) => void;
  pushRecentQuery: (query: string) => void;
  toggleFavorite: (id: string) => void;
  setAuth: (token: string, username: string) => void;
  logout: () => void;
  addToCart: (product: Product) => void;
  removeFromCart: (productId: string) => void;
}

function loadToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

function loadUsername(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_username");
}

export const useAppStore = create<AppState>((set) => ({
  activeStore: "lider",
  recentQueries: ["arroz 1 kilo", "leche entera 1 litro", "aceite 1 litro"],
  favoriteProductIds: [],
  authToken: loadToken(),
  authUsername: loadUsername(),
  cart: [],
  cartCount: 0,

  setActiveStore: (store) => set({ activeStore: store }),

  pushRecentQuery: (query) =>
    set((state) => ({
      recentQueries: [query, ...state.recentQueries.filter((item) => item !== query)].slice(0, 8),
    })),

  toggleFavorite: (id) =>
    set((state) => ({
      favoriteProductIds: state.favoriteProductIds.includes(id)
        ? state.favoriteProductIds.filter((item) => item !== id)
        : [...state.favoriteProductIds, id],
    })),

  setAuth: (token, username) => {
    localStorage.setItem("auth_token", token);
    localStorage.setItem("auth_username", username);
    set({ authToken: token, authUsername: username });
  },

  logout: () => {
    // Revoke token server-side so it cannot be reused after logout
    const token = localStorage.getItem("auth_token");
    if (token) {
      fetch("/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {
        // Silent — local state is cleared regardless of server response
      });
    }
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_username");
    set({ authToken: null, authUsername: null });
  },

  addToCart: (product) =>
    set((state) => {
      const id = product.sku ?? product.id ?? product.name;
      const existing = state.cart.find(
        (item) => (item.product.sku ?? item.product.id ?? item.product.name) === id
      );
      const cart = existing
        ? state.cart.map((item) =>
            (item.product.sku ?? item.product.id ?? item.product.name) === id
              ? { ...item, quantity: item.quantity + 1 }
              : item
          )
        : [...state.cart, { product, quantity: 1 }];
      return { cart, cartCount: cart.reduce((sum, i) => sum + i.quantity, 0) };
    }),

  removeFromCart: (productId) =>
    set((state) => {
      const cart = state.cart.filter(
        (item) => (item.product.sku ?? item.product.id ?? item.product.name) !== productId
      );
      return { cart, cartCount: cart.reduce((sum, i) => sum + i.quantity, 0) };
    }),
}));
