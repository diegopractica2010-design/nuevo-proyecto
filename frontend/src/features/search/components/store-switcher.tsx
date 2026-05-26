"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, ShoppingBag, Store } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { apiClient } from "@/services/api-client";
import type { StoreId, StoreInfo } from "@/types/api";

const FALLBACK_STORES: StoreInfo[] = [
  { id: "lider", display_name: "Lider", experimental: false },
  { id: "jumbo", display_name: "Jumbo", experimental: true },
];

function StoreIcon({ id }: { id: string }) {
  if (id === "lider") return <Building2 className="h-4 w-4" />;
  if (id === "jumbo") return <ShoppingBag className="h-4 w-4" />;
  return <Store className="h-4 w-4" />;
}

export function StoreSwitcher({
  value,
  onChange
}: {
  value: StoreId;
  onChange: (store: StoreId) => void;
}) {
  const { data: stores = FALLBACK_STORES } = useQuery({
    queryKey: ["stores"],
    queryFn: () => apiClient.getStores(),
    staleTime: Infinity,
  });

  return (
    <div
      className="grid rounded-lg border border-white/10 bg-black/20 p-1"
      style={{ gridTemplateColumns: `repeat(${stores.length}, minmax(0, 1fr))` }}
    >
      {stores.map((store) => (
        <Button
          key={store.id}
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onChange(store.id)}
          className={cn(
            "h-9 justify-center rounded-md text-xs",
            value === store.id ? "bg-white/10 text-foreground shadow-sm" : "text-muted-foreground"
          )}
        >
          <StoreIcon id={store.id} />
          {store.display_name}
        </Button>
      ))}
    </div>
  );
}
