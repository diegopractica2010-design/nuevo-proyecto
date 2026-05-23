"use client";

import { ProductCard } from "./product-card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Product } from "@/types/api";

export function ProductGrid({
  products,
  isLoading
}: {
  products: Product[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-32" />
        ))}
      </div>
    );
  }

  if (!products.length) {
    return (
      <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed border-white/10 bg-white/[0.035] p-8 text-center">
        <div>
          <p className="text-sm font-medium">Sin resultados cargados</p>
          <p className="mt-1 text-sm text-muted-foreground">Busca un producto para comparar precios reales.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {products.map((product, index) => (
        <ProductCard key={`${product.source}-${product.sku ?? product.id ?? product.name}-${index}`} product={product} index={index} />
      ))}
    </div>
  );
}
