"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import {
  ArrowDownUp, CheckCircle2, Download, Loader2, ShieldQuestion, ShoppingBasket,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useShoppingListCompare } from "@/hooks/use-shopping-list";
import { formatCurrency, cn } from "@/lib/utils";
import type { CompareItemResult } from "@/types/api";

// ── Count-up total ─────────────────────────────────────────────────────────

function CountUp({ target }: { target: number }) {
  const mv = useMotionValue(0);
  const display = useTransform(mv, (v: number) =>
    new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(v)
  );
  const prev = useRef(0);

  useEffect(() => {
    const ctrl = animate(mv, target, { duration: 0.8, ease: "easeOut" });
    prev.current = target;
    return () => ctrl.stop();
  }, [mv, target]);

  return <motion.span>{display}</motion.span>;
}

// ── Result row ─────────────────────────────────────────────────────────────

function ResultRow({ item, index }: { item: CompareItemResult; index: number }) {
  const found = item.status === "matched";
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
      className="flex items-start gap-3 rounded-xl border border-border bg-background p-3"
    >
      <span className="mt-0.5 shrink-0">
        {found ? (
          <CheckCircle2 className="h-4 w-4 text-primary" />
        ) : (
          <ShieldQuestion className="h-4 w-4 text-amber-500" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{item.query}</p>
        <div className="mt-1 grid gap-1 sm:grid-cols-2">
          {item.stores.map((s) => (
            <div key={s.store} className="text-xs text-muted-foreground">
              <span className="capitalize font-medium">{s.store}</span>:{" "}
              {s.best ? formatCurrency(s.best.price) : "—"}
            </div>
          ))}
        </div>
      </div>
      <p className="shrink-0 text-sm font-semibold text-foreground">
        {item.cheapest ? formatCurrency(item.cheapest.price) : "—"}
      </p>
    </motion.div>
  );
}

// ── Export helper ──────────────────────────────────────────────────────────

function exportTxt(items: CompareItemResult[]) {
  const lines = items.map((item) => {
    const price = item.cheapest ? formatCurrency(item.cheapest.price) : "—";
    const store = item.cheapest?.source ?? "?";
    return `${item.query.padEnd(30)} ${price}  (${store})`;
  });
  const total = items.reduce((s, i) => s + (i.cheapest?.price ?? 0), 0);
  lines.push("", `Total estimado: ${formatCurrency(total)}`);
  const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "lista-radar.txt";
  a.click();
  URL.revokeObjectURL(url);
}

// ── Main component ─────────────────────────────────────────────────────────

const STARTER = `arroz 1 kilo\nleche entera 1 litro\naceite 1 litro\ndetergente ropa\npapel higiénico`;

export function ShoppingListWorkbench() {
  const [value, setValue] = useState(STARTER);
  const compare = useShoppingListCompare();
  const items = value.split("\n").map((l) => l.trim()).filter(Boolean).slice(0, 40);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (items.length) compare.mutate(items);
  }

  return (
    <section id="compare" className="grid gap-4 md:grid-cols-[22rem_1fr]">
      {/* ── Left: input ── */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <ShoppingBasket className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Lista de compras</h2>
        </div>
        <form onSubmit={onSubmit} className="space-y-3">
          <Textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            rows={10}
            className="resize-none rounded-lg text-sm"
            placeholder="Un producto por línea…"
          />
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">{items.length} productos</span>
            <Button size="sm" disabled={compare.isPending || !items.length}>
              {compare.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ArrowDownUp className="h-3.5 w-3.5" />
              )}
              Comparar
            </Button>
          </div>
        </form>
      </div>

      {/* ── Right: results ── */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        {compare.isPending ? (
          <div className="flex h-full min-h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Calculando mejor canasta…
          </div>
        ) : compare.data ? (
          <div className="space-y-4">
            {/* Total */}
            <div className="flex items-center justify-between rounded-xl border border-primary/20 bg-primary/5 px-4 py-3">
              <div>
                <p className="text-xs text-muted-foreground">Total estimado</p>
                <p className="text-2xl font-bold text-primary">
                  <CountUp target={compare.data.estimated_total} />
                </p>
                <p className="text-xs text-muted-foreground">
                  {compare.data.matched_count}/{compare.data.count} productos encontrados
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => exportTxt(compare.data!.items)}
                className="gap-1.5"
              >
                <Download className="h-3.5 w-3.5" />
                Exportar
              </Button>
            </div>

            {/* Items */}
            <div className="space-y-2">
              {compare.data.items.map((item, i) => (
                <ResultRow key={item.query} item={item} index={i} />
              ))}
            </div>
          </div>
        ) : (
          <div className="flex h-full min-h-48 flex-col items-center justify-center gap-2 text-center">
            <ShoppingBasket className="h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Escribe tu lista y pulsa <strong>Comparar</strong>
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
