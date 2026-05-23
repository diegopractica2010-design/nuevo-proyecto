"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/api-client";
import type { StoreId } from "@/types/api";

export function useSearchProducts(query: string, store: StoreId) {
  return useQuery({
    queryKey: ["search", store, query],
    queryFn: () => apiClient.searchProducts({ query, store }),
    enabled: query.trim().length > 0,
    staleTime: 60_000,
    gcTime: 10 * 60_000,
    retry: 1
  });
}
