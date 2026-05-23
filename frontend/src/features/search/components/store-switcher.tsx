"use client";

import { Building2, ShoppingBag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { StoreId } from "@/types/api";

const stores: Array<{ id: StoreId; label: string; icon: typeof Building2 }> = [
  { id: "lider", label: "Lider", icon: Building2 },
  { id: "jumbo", label: "Jumbo", icon: ShoppingBag }
];

export function StoreSwitcher({
  value,
  onChange
}: {
  value: StoreId;
  onChange: (store: StoreId) => void;
}) {
  return (
    <div className="grid grid-cols-2 rounded-lg border border-white/10 bg-black/20 p-1">
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
          <store.icon className="h-4 w-4" />
          {store.label}
        </Button>
      ))}
    </div>
  );
}
