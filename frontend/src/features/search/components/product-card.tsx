"use client";

import Image from "next/image";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, LineChart, PackageCheck, Plus, Trophy } from "lucide-react";
import { PriceHistoryChart } from "@/features/search/components/price-history-chart";
import { cardEntrance } from "@/lib/design-tokens";
import { formatCurrency, cn } from "@/lib/utils";
import { useAppStore } from "@/stores/use-app-store";
import type { Product, StoreId } from "@/types/api";

export function ProductCard({
  product,
  index,
  isCheapest = false,
}: {
  product: Product;
  index: number;
  isCheapest?: boolean;
}) {
  const addToCart = useAppStore((s) => s.addToCart);
  const [showHistory, setShowHistory] = useState(false);
  const [pressed, setPressed] = useState(false);

  const productId = product.sku ?? product.id ?? `${product.source}-${product.name}`;
  const storeId: StoreId | null = product.source || null;

  function handleAdd() {
    addToCart(product);
    setPressed(true);
    setTimeout(() => setPressed(false), 600);
  }

  return (
    <motion.div {...cardEntrance(index)}>
      <div
        className={cn(
          "overflow-hidden rounded-xl border bg-card transition-shadow duration-200 hover:shadow-md",
          isCheapest
            ? "border-primary/30 ring-1 ring-primary/20"
            : "border-slate-100 dark:border-slate-800"
        )}
      >
        <div className="flex gap-3 p-4">
          {/* Image */}
          <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-slate-50 dark:bg-slate-800">
            {product.image ? (
              <Image
                src={product.image}
                alt={product.name}
                fill
                sizes="80px"
                className="object-contain p-2"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-muted-foreground/40">
                <PackageCheck className="h-6 w-6" />
              </div>
            )}
          </div>

          {/* Info */}
          <div className="min-w-0 flex-1">
            {/* Name + badges */}
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                {isCheapest && (
                  <span className="mb-1 inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                    <Trophy className="h-2.5 w-2.5" />
                    Mejor precio
                  </span>
                )}
                <p className="line-clamp-2 text-sm font-medium leading-snug text-foreground">
                  {product.name}
                </p>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {product.brand ?? product.seller ?? product.source}
                </p>
              </div>

              {/* Add to cart */}
              <motion.button
                animate={pressed ? { scale: [1, 1.3, 1] } : { scale: 1 }}
                transition={{ duration: 0.3 }}
                onClick={handleAdd}
                aria-label="Agregar al carro"
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-colors duration-200",
                  "border-primary/30 bg-primary/5 text-primary hover:bg-primary hover:text-primary-foreground"
                )}
              >
                <Plus className="h-3.5 w-3.5" />
              </motion.button>
            </div>

            {/* Price row */}
            <div className="mt-3 flex items-end justify-between gap-2">
              <div>
                <p
                  className={cn(
                    "text-xl font-bold leading-none",
                    isCheapest ? "text-primary" : "text-foreground"
                  )}
                >
                  {formatCurrency(product.price)}
                </p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  {product.unit_price ?? ""}
                </p>
              </div>

              <div className="flex items-center gap-1">
                {product.is_offer && (
                  <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                    Oferta
                  </span>
                )}
                {storeId && productId && (
                  <button
                    onClick={() => setShowHistory((v) => !v)}
                    aria-label="Ver historial de precio"
                    className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    <LineChart className="h-3.5 w-3.5" />
                  </button>
                )}
                {product.url && (
                  <a
                    href={product.url}
                    target="_blank"
                    rel="noreferrer"
                    aria-label="Ver en tienda"
                    className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Price history */}
        <AnimatePresence>
          {showHistory && storeId && productId && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden border-t border-border/50 px-4 pb-4 pt-3"
            >
              <PriceHistoryChart product_id={productId} store={storeId} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
