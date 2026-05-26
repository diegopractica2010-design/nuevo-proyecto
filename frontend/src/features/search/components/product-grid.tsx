"use client";

import { ProductCard } from "./product-card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Product } from "@/types/api";

export function ProductGrid({
  products,
  isLoading,
  emptyQuery,
}: {
  products: Product[];
  isLoading: boolean;
  emptyQuery?: string;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-3 md:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!products.length) {
    return (
      <div className="flex min-h-48 items-center justify-center rounded-xl border border-dashed border-border bg-muted/40 p-8 text-center">
        <div>
          <p className="text-sm font-medium text-foreground">
            {emptyQuery ? `Sin resultados para "${emptyQuery}"` : "Sin resultados"}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Prueba con otro término o cambia de tienda.
          </p>
        </div>
      </div>
    );
  }

  const minPrice = Math.min(...products.map((p) => p.price));

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {products.map((product, index) => (
        <ProductCard
          key={`${product.source}-${product.sku ?? product.id ?? product.name}-${index}`}
          product={product}
          index={index}
          isCheapest={product.price === minPrice}
        />
      ))}
    </div>
  );
}
