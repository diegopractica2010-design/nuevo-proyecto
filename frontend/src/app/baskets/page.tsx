"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown, ChevronRight, Loader2, Minus, Plus, ShoppingCart, Trash2,
} from "lucide-react";
import { AppLayout } from "@/layouts/app-layout";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/services/api-client";
import { useAppStore } from "@/stores/use-app-store";
import { formatCurrency, cn } from "@/lib/utils";
import type { Basket, BasketSummary } from "@/types/api";

// ── Basket row ─────────────────────────────────────────────────────────────

function BasketRow({ summary }: { summary: BasketSummary }) {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const { data: basket } = useQuery<Basket>({
    queryKey: ["basket", summary.id],
    queryFn: () => apiClient.getBasket(summary.id),
    enabled: open,
  });

  const updateQty = useMutation({
    mutationFn: ({ productId, qty }: { productId: string; qty: number }) =>
      apiClient.updateBasketItem(summary.id, productId, qty),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["basket", summary.id] }),
  });

  const runningTotal =
    basket?.items.reduce((s, i) => s + i.price * i.quantity, 0) ?? summary.total_price;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      {/* Header row */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-4 p-4 text-left transition-colors hover:bg-muted/40"
      >
        <div className="flex items-center gap-3">
          <ShoppingCart className="h-4 w-4 shrink-0 text-primary" />
          <div>
            <p className="text-sm font-semibold text-foreground">{summary.name}</p>
            <p className="text-xs text-muted-foreground">
              {summary.item_count} producto{summary.item_count !== 1 ? "s" : ""}
              {summary.stores.length > 0 && ` · ${summary.stores.join(", ")}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-primary">
            {formatCurrency(runningTotal)}
          </span>
          {open ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Detail */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-4 pb-4 pt-3">
              {!basket ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : basket.items.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Cesta vacía</p>
              ) : (
                <div className="space-y-2">
                  {basket.items.map((item) => (
                    <div
                      key={item.product_id}
                      className="flex items-center gap-3 rounded-lg border border-border/60 bg-background p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-1 text-sm font-medium text-foreground">
                          {item.name}
                        </p>
                        <p className="text-xs capitalize text-muted-foreground">{item.store}</p>
                      </div>

                      {/* Qty control */}
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() =>
                            item.quantity > 1
                              ? updateQty.mutate({ productId: item.product_id, qty: item.quantity - 1 })
                              : undefined
                          }
                          disabled={item.quantity <= 1 || updateQty.isPending}
                          className={cn(
                            "flex h-6 w-6 items-center justify-center rounded-md border border-border",
                            "text-muted-foreground transition-colors hover:bg-muted disabled:opacity-40"
                          )}
                        >
                          <Minus className="h-3 w-3" />
                        </button>
                        <span className="w-6 text-center text-xs font-medium">{item.quantity}</span>
                        <button
                          onClick={() =>
                            updateQty.mutate({ productId: item.product_id, qty: item.quantity + 1 })
                          }
                          disabled={updateQty.isPending}
                          className={cn(
                            "flex h-6 w-6 items-center justify-center rounded-md border border-border",
                            "text-muted-foreground transition-colors hover:bg-muted disabled:opacity-40"
                          )}
                        >
                          <Plus className="h-3 w-3" />
                        </button>
                      </div>

                      <p className="w-20 text-right text-sm font-semibold text-foreground">
                        {formatCurrency(item.price * item.quantity)}
                      </p>
                    </div>
                  ))}

                  {/* Running total */}
                  <div className="mt-3 flex justify-between border-t border-border pt-3">
                    <span className="text-sm text-muted-foreground">Total</span>
                    <span className="text-sm font-bold text-primary">
                      {formatCurrency(runningTotal)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function BasketsPage() {
  const router = useRouter();
  const authToken = useAppStore((s) => s.authToken);

  useEffect(() => {
    if (!authToken) router.push("/");
  }, [authToken, router]);

  const { data: baskets, isLoading } = useQuery<BasketSummary[]>({
    queryKey: ["baskets"],
    queryFn: () => apiClient.getBaskets(),
    enabled: !!authToken,
  });

  if (!authToken) return null;

  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Mis cestas</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Gestiona tus listas guardadas y revisa los totales.
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : !baskets?.length ? (
          <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-muted/30 text-center">
            <ShoppingCart className="h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Aún no tienes cestas. Agrega productos desde la búsqueda.
            </p>
            <Button size="sm" variant="outline" onClick={() => router.push("/")}>
              Ir a buscar
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {baskets.map((b) => (
              <BasketRow key={b.id} summary={b} />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
