"use client";

import { FormEvent, useEffect, useState } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import {
  ArrowDownUp, CheckCircle2, Download, Loader2, ShieldQuestion, ShoppingBasket, Trophy,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useShoppingListCompare } from "@/hooks/use-shopping-list";
import { formatCurrency, cn } from "@/lib/utils";
import type { CompareItemResult } from "@/types/api";

// ── Store display info ─────────────────────────────────────────────────────

const STORE_INFO: Record<string, { label: string; color: string }> = {
  lider:        { label: "Lider",        color: "#00913f" },
  jumbo:        { label: "Jumbo",        color: "#e5002b" },
  santa_isabel: { label: "Santa Isabel", color: "#e5002b" },
  acuenta:      { label: "Acuenta",      color: "#f6a800" },
  tottus:       { label: "Tottus",       color: "#e5002b" },
  unimarc:      { label: "Unimarc",      color: "#003da5" },
};

// ── Count-up total ─────────────────────────────────────────────────────────

function CountUp({ target }: { target: number }) {
  const mv = useMotionValue(0);
  const display = useTransform(mv, (v: number) =>
    new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(v)
  );

  useEffect(() => {
    const ctrl = animate(mv, target, { duration: 0.8, ease: "easeOut" });
    return () => ctrl.stop();
  }, [mv, target]);

  return <motion.span>{display}</motion.span>;
}

// ── Result row ─────────────────────────────────────────────────────────────

function ResultRow({ item, index }: { item: CompareItemResult; index: number }) {
  const found = item.status === "matched";
  const cheapestStore = item.cheapest?.source ?? null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-xl border border-border bg-background overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/60">
        {found ? (
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[#00913f]" />
        ) : (
          <ShieldQuestion className="h-3.5 w-3.5 shrink-0 text-amber-500" />
        )}
        <p className="flex-1 text-sm font-semibold text-foreground truncate">{item.query}</p>
        {item.cheapest && (
          <p className="shrink-0 text-sm font-bold text-[#00913f]">
            {formatCurrency(item.cheapest.price)}
          </p>
        )}
      </div>

      {/* Per-store prices */}
      <div className="grid grid-cols-2 gap-px bg-border sm:grid-cols-3">
        {item.stores.map((s) => {
          const info = STORE_INFO[s.store] ?? { label: s.store, color: "#666" };
          const isCheapest = s.store === cheapestStore && !!s.best;
          return (
            <div
              key={s.store}
              className={cn(
                "flex items-center justify-between gap-1 bg-background px-2.5 py-1.5",
                isCheapest && "bg-[#00913f]/5"
              )}
            >
              <div className="flex items-center gap-1 min-w-0">
                {isCheapest && <Trophy className="h-3 w-3 shrink-0 text-[#00913f]" />}
                <span
                  className="text-[10px] font-bold truncate"
                  style={{ color: info.color }}
                >
                  {info.label}
                </span>
              </div>
              <span
                className={cn(
                  "text-xs font-semibold shrink-0",
                  isCheapest ? "text-[#00913f]" : "text-foreground"
                )}
              >
                {s.best ? formatCurrency(s.best.price) : "—"}
              </span>
            </div>
          );
        })}
      </div>
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

const STARTER = `arroz\nleche\naceite\ndetergente\nconfort`;

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
            <Button
              type="submit"
              size="sm"
              disabled={compare.isPending || !items.length}
              style={{ background: "#00913f" }}
              className="gap-1.5 text-white"
            >
              {compare.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ArrowDownUp className="h-3.5 w-3.5" />
              )}
              {compare.isPending ? "Comparando…" : "Comparar"}
            </Button>
          </div>
        </form>

        {/* Hint */}
        <p className="mt-3 text-[11px] text-muted-foreground">
          Escribe un producto por línea. Buscaremos el mejor precio en Lider, Jumbo y Santa Isabel.
        </p>
      </div>

      {/* ── Right: results ── */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        {compare.isPending ? (
          <div className="flex h-full min-h-48 flex-col items-center justify-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin text-[#00913f]" />
            <div className="text-center">
              <p className="font-medium text-foreground">Comparando precios…</p>
              <p className="text-xs mt-0.5">Esto puede tardar 10–20 segundos</p>
            </div>
          </div>
        ) : compare.isError ? (
          <div className="flex h-full min-h-48 flex-col items-center justify-center gap-2 text-center">
            <p className="text-2xl">⚠️</p>
            <p className="text-sm font-semibold text-foreground">No se pudo comparar</p>
            <p className="text-xs text-muted-foreground">
              {(compare.error as Error)?.message ?? "Verifica tu conexión e intenta de nuevo."}
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              onClick={() => compare.mutate(items)}
            >
              Reintentar
            </Button>
          </div>
        ) : compare.data ? (
          <div className="space-y-4">
            {/* Total */}
            <div className="flex items-center justify-between rounded-xl border border-[#00913f]/20 bg-[#00913f]/5 px-4 py-3">
              <div>
                <p className="text-xs text-muted-foreground">Total estimado (precio más bajo)</p>
                <p className="text-2xl font-bold text-[#00913f]">
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
            <p className="text-sm font-semibold text-foreground">Compara tu canasta</p>
            <p className="text-xs text-muted-foreground">
              Escribe tu lista y pulsa <strong>Comparar</strong> para ver el precio más bajo por tienda.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
