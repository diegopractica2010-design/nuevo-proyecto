"use client";

import Image from "next/image";
import { useState } from "react";
import { ExternalLink, Heart, LineChart, PackageCheck } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PriceHistoryChart } from "@/features/search/components/price-history-chart";
import { formatCurrency } from "@/lib/utils";
import { useAppStore } from "@/stores/use-app-store";
import type { Product, StoreId } from "@/types/api";

export function ProductCard({ product, index }: { product: Product; index: number }) {
  const favoriteProductIds = useAppStore((state) => state.favoriteProductIds);
  const toggleFavorite = useAppStore((state) => state.toggleFavorite);
  const productId = product.sku ?? product.id ?? `${product.source}-${product.name}`;
  const isFavorite = favoriteProductIds.includes(productId);
  const [showHistory, setShowHistory] = useState(false);
  const storeId = (product.source === "lider" || product.source === "jumbo") ? product.source as StoreId : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(index * 0.025, 0.18) }}
    >
      <Card className="group overflow-hidden">
        <div className="flex gap-4 p-4">
          <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg border border-white/10 bg-white/6">
            {product.image ? (
              <Image src={product.image} alt={product.name} fill sizes="80px" className="object-contain p-2" />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-muted-foreground">
                <PackageCheck className="h-7 w-7" />
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="line-clamp-2 text-sm font-medium leading-5">{product.name}</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">{product.brand ?? product.seller ?? product.source}</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0"
                onClick={() => toggleFavorite(productId)}
                aria-label="Favorite product"
              >
                <Heart className={isFavorite ? "h-4 w-4 fill-primary text-primary" : "h-4 w-4"} />
              </Button>
            </div>
            <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xl font-semibold tracking-normal">{formatCurrency(product.price)}</p>
                <p className="text-xs text-muted-foreground">{product.unit_price ?? "Precio unitario no informado"}</p>
              </div>
              <div className="flex items-center gap-2">
                {product.is_offer ? <Badge variant="success">Oferta</Badge> : null}
                {storeId && productId && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8"
                    onClick={() => setShowHistory((v) => !v)}
                    aria-label="Price history"
                  >
                    <LineChart className="h-3.5 w-3.5" />
                  </Button>
                )}
                {product.url ? (
                  <Button asChild variant="outline" size="sm">
                    <a href={product.url} target="_blank" rel="noreferrer">
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </Button>
                ) : null}
              </div>
            </div>
          </div>
        </div>

        <AnimatePresence>
          {showHistory && storeId && productId && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden border-t border-white/10 px-4 pb-4 pt-3"
            >
              <PriceHistoryChart product_id={productId} store={storeId} />
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.div>
  );
}
