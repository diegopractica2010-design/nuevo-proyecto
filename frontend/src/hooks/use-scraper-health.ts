"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/api-client";

export function useScraperHealth() {
  return useQuery({
    queryKey: ["scraper-health"],
    queryFn: apiClient.getScraperHealth,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1
  });
}
