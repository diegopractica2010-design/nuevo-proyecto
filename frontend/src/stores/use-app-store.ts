import { create } from "zustand";
import type { StoreId } from "@/types/api";

interface AppState {
  activeStore: StoreId;
  recentQueries: string[];
  favoriteProductIds: string[];
  authToken: string | null;
  authUsername: string | null;
  setActiveStore: (store: StoreId) => void;
  pushRecentQuery: (query: string) => void;
  toggleFavorite: (id: string) => void;
  setAuth: (token: string, username: string) => void;
  logout: () => void;
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
  setActiveStore: (store) => set({ activeStore: store }),
  pushRecentQuery: (query) =>
    set((state) => ({
      recentQueries: [query, ...state.recentQueries.filter((item) => item !== query)].slice(0, 8)
    })),
  toggleFavorite: (id) =>
    set((state) => ({
      favoriteProductIds: state.favoriteProductIds.includes(id)
        ? state.favoriteProductIds.filter((item) => item !== id)
        : [...state.favoriteProductIds, id]
    })),
  setAuth: (token, username) => {
    localStorage.setItem("auth_token", token);
    localStorage.setItem("auth_username", username);
    set({ authToken: token, authUsername: username });
  },
  logout: () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_username");
    set({ authToken: null, authUsername: null });
  }
}));
