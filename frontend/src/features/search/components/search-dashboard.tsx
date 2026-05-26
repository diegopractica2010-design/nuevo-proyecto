"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Coffee, Milk, ShoppingBag, Sparkles, Wheat, Wind,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSearchProducts } from "@/hooks/use-search-products";
import { useAppStore } from "@/stores/use-app-store";
import { cn } from "@/lib/utils";
import { ProductGrid } from "./product-grid";

// ── Rotating placeholder ───────────────────────────────────────────────────

const PLACEHOLDERS = [
  "leche entera 1 litro…",
  "arroz 1 kilo…",
  "detergente ropa…",
  "yogur frutilla…",
  "aceite maravilla 1 litro…",
  "papel higiénico…",
  "jugo naranja 1 litro…",
];

function useCyclingPlaceholder(strings: string[], ms = 2600) {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % strings.length), ms);
    return () => clearInterval(id);
  }, [strings, ms]);
  return strings[index];
}

// ── Quick pills ────────────────────────────────────────────────────────────

const PILLS: Array<{ label: string; icon: typeof Milk; q: string }> = [
  { label: "Leche",       icon: Milk,       q: "leche entera 1 litro" },
  { label: "Arroz",       icon: Wheat,      q: "arroz 1 kilo" },
  { label: "Café",        icon: Coffee,     q: "café molido" },
  { label: "Detergente",  icon: Wind,       q: "detergente ropa" },
  { label: "Bolsas",      icon: ShoppingBag,q: "bolsas basura" },
];

// ── Component ──────────────────────────────────────────────────────────────

export function SearchDashboard() {
  const activeStore = useAppStore((s) => s.activeStore);
  const pushRecentQuery = useAppStore((s) => s.pushRecentQuery);
  const recentQueries = useAppStore((s) => s.recentQueries);

  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const placeholder = useCyclingPlaceholder(PLACEHOLDERS);
  const search = useSearchProducts(query, activeStore);

  function fire(q: string) {
    const trimmed = q.trim();
    if (!trimmed) return;
    setDraft(trimmed);
    setQuery(trimmed);
    pushRecentQuery(trimmed);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    fire(draft);
  }

  return (
    <section className="space-y-8">
      {/* ── Hero ── */}
      <div className="flex flex-col items-center gap-6 pt-4 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl"
        >
          ¿Qué vas a comprar hoy?
        </motion.h1>

        <motion.form
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.06 }}
          onSubmit={onSubmit}
          className="relative w-full max-w-xl"
        >
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={placeholder}
            className={cn(
              "h-14 w-full rounded-xl border border-border bg-background px-5 pr-24",
              "text-[15px] shadow-sm outline-none ring-0",
              "placeholder:text-muted-foreground/60",
              "focus:border-primary focus:ring-2 focus:ring-primary/20",
              "transition-all duration-200"
            )}
          />
          <Button
            type="submit"
            size="sm"
            className="absolute right-2 top-1/2 -translate-y-1/2 gap-1.5 rounded-lg px-4"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Buscar
          </Button>
        </motion.form>

        {/* Quick pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.12 }}
          className="flex flex-wrap justify-center gap-2"
        >
          {PILLS.map(({ label, icon: Icon, q }) => (
            <button
              key={label}
              type="button"
              onClick={() => fire(q)}
              className={cn(
                "flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5",
                "text-xs font-medium text-muted-foreground",
                "transition-all duration-200 hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
              )}
            >
              <Icon className="h-3 w-3" />
              {label}
            </button>
          ))}
        </motion.div>

        {/* Recent queries */}
        <AnimatePresence>
          {recentQueries.length > 0 && !query && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-wrap justify-center gap-1.5"
            >
              <span className="text-xs text-muted-foreground">Recientes:</span>
              {recentQueries.slice(0, 5).map((q) => (
                <button
                  key={q}
                  onClick={() => fire(q)}
                  className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                >
                  {q}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Results ── */}
      <AnimatePresence mode="wait">
        {query && (
          <motion.div
            key={query + activeStore}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {search.data && search.data.count > 0 && (
              <p className="mb-4 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">{search.data.count}</span> resultados
                para &ldquo;{query}&rdquo; en{" "}
                <span className="font-medium capitalize text-foreground">{activeStore}</span>
                {search.data.strategy ? (
                  <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-[10px]">
                    {search.data.strategy}
                  </span>
                ) : null}
              </p>
            )}
            <ProductGrid
              products={search.data?.results ?? []}
              isLoading={search.isFetching}
              emptyQuery={query}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
