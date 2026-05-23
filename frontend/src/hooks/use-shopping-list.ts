"use client";

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/services/api-client";

export function useShoppingListCompare() {
  return useMutation({
    mutationKey: ["shopping-list-compare"],
    mutationFn: (items: string[]) => apiClient.compareShoppingList(items)
  });
}
