import { create } from "zustand";
import type { StoreId } from "@/types/api";

interface AppState {
  activeStore: StoreId;
  recentQueries: string[];
  favoriteProductIds: string[];
  setActiveStore: (store: StoreId) => void;
  pushRecentQuery: (query: string) => void;
  toggleFavorite: (id: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeStore: "lider",
  recentQueries: ["arroz 1 kilo", "leche entera 1 litro", "aceite 1 litro"],
  favoriteProductIds: [],
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
    }))
}));
