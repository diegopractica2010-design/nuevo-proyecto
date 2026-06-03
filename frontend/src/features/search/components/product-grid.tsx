"use client";

import { useMemo } from "react";
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
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {Array.from({ length: 10 }).map((_, i) => (
          <Skeleton key={i} className="h-72 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!products.length) {
    return (
      <div className="flex min-h-48 items-center justify-center rounded-xl border border-dashed border-[#e8eaed] bg-white p-8 text-center shadow-sm">
        <div>
          <p className="text-2xl">🔍</p>
          <p className="mt-2 text-sm font-semibold text-[#1a2332]">
            {emptyQuery ? `Sin resultados para "${emptyQuery}"` : "Sin resultados"}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Prueba con otro término o cambia de tienda.
          </p>
        </div>
      </div>
    );
  }

  const minPrice = useMemo(
    () => products.reduce((min, p) => (p.price > 0 && p.price < min ? p.price : min), Infinity),
    [products]
  );

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {products.map((product, index) => (
        <ProductCard
          key={`${product.source}-${product.sku ?? product.id ?? product.name}-${index}`}
          product={product}
          index={index}
          isCheapest={product.price > 0 && product.price === minPrice}
        />
      ))}
    </div>
  );
}
