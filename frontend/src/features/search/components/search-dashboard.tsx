"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowDown01, ArrowUp01, ArrowDownUp, Coffee, Milk, ShoppingBag, Sparkles, Wheat, Wind,
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
  { label: "Leche",       icon: Milk,        q: "leche entera 1 litro" },
  { label: "Arroz",       icon: Wheat,       q: "arroz 1 kilo" },
  { label: "Café",        icon: Coffee,      q: "café molido" },
  { label: "Detergente",  icon: Wind,        q: "detergente ropa" },
  { label: "Bolsas",      icon: ShoppingBag, q: "bolsas basura" },
];

type SortOrder = "default" | "asc" | "desc";

// ── Component ──────────────────────────────────────────────────────────────

export function SearchDashboard() {
  const activeStore   = useAppStore((s) => s.activeStore);
  const pushRecentQuery = useAppStore((s) => s.pushRecentQuery);
  const recentQueries = useAppStore((s) => s.recentQueries);

  const [draft, setDraft]             = useState("");
  const [query, setQuery]             = useState("");
  const [sortOrder, setSortOrder]     = useState<SortOrder>("default");
  const [brandFilter, setBrandFilter] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [priceRange, setPriceRange]   = useState<[number, number] | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const placeholder = useCyclingPlaceholder(PLACEHOLDERS);
  const search = useSearchProducts(query, activeStore);

  const facetPriceMin = search.data?.facets.price_range.min ?? null;
  const facetPriceMax = search.data?.facets.price_range.max ?? null;

  // Reset controls when query or store changes
  useEffect(() => {
    setSortOrder("default");
    setBrandFilter(null);
    setCategoryFilter(null);
    setPriceRange(null);
  }, [query, activeStore]);

  const activeFilterCount =
    (brandFilter ? 1 : 0) + (categoryFilter ? 1 : 0) + (priceRange ? 1 : 0);

  function clearAllFilters() {
    setBrandFilter(null);
    setCategoryFilter(null);
    setPriceRange(null);
  }

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

  const allProducts  = search.data?.results ?? [];
  const brands       = search.data?.facets.brands ?? [];
  const categories   = search.data?.facets.categories ?? [];

  const filteredSorted = useMemo(() => {
    let list = allProducts;
    if (brandFilter) list = list.filter((p) => p.brand === brandFilter);
    if (categoryFilter) list = list.filter((p) => p.category === categoryFilter);
    if (priceRange) list = list.filter((p) => p.price >= priceRange[0] && p.price <= priceRange[1]);
    if (sortOrder === "asc")  list = [...list].sort((a, b) => a.price - b.price);
    if (sortOrder === "desc") list = [...list].sort((a, b) => b.price - a.price);
    return list;
  }, [allProducts, sortOrder, brandFilter, categoryFilter, priceRange]);

  const hasResults = !!search.data && search.data.count > 0;

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
          role="search"
          className="relative w-full max-w-xl"
        >
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={placeholder}
            aria-label="Buscar productos"
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
            className="space-y-4"
          >
            {/* Result count + controls bar */}
            {hasResults && (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground" aria-live="polite" aria-atomic="true">
                  <span className="font-medium text-foreground">{search.data!.count}</span>{" "}
                  resultados para &ldquo;{query}&rdquo;
                  {search.data?.strategy ? (
                    <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-[10px]">
                      {search.data.strategy}
                    </span>
                  ) : null}
                </p>

                {/* Sort buttons */}
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">Precio:</span>
                  <button
                    type="button"
                    onClick={() => setSortOrder(sortOrder === "asc" ? "default" : "asc")}
                    className={cn(
                      "flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors",
                      sortOrder === "asc"
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-primary"
                    )}
                  >
                    <ArrowUp01 className="h-3.5 w-3.5" />
                    Menor
                  </button>
                  <button
                    type="button"
                    onClick={() => setSortOrder(sortOrder === "desc" ? "default" : "desc")}
                    className={cn(
                      "flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors",
                      sortOrder === "desc"
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-primary"
                    )}
                  >
                    <ArrowDown01 className="h-3.5 w-3.5" />
                    Mayor
                  </button>
                  {sortOrder !== "default" && (
                    <button
                      type="button"
                      onClick={() => setSortOrder("default")}
                      className="flex items-center gap-1 rounded-lg border border-border bg-background px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
                    >
                      <ArrowDownUp className="h-3 w-3" />
                      Relevancia
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Filters bar */}
            {hasResults && (
              <div className="space-y-2">
                {/* Active filter count + clear all */}
                {activeFilterCount > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-primary-foreground">
                      {activeFilterCount} filtro{activeFilterCount > 1 ? "s" : ""}
                    </span>
                    <button
                      type="button"
                      onClick={clearAllFilters}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      Limpiar todo
                    </button>
                  </div>
                )}

                {/* Brand chips */}
                {brands.length > 1 && (
                  <div role="group" aria-label="Filtrar por marca" className="flex flex-wrap gap-1.5">
                    {brandFilter && (
                      <button type="button" onClick={() => setBrandFilter(null)}
                        aria-pressed="true"
                        className="rounded-full border border-primary bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/20">
                        ✕ {brandFilter}
                      </button>
                    )}
                    {brands.slice(0, 8).map(({ name, count }) =>
                      name && name !== brandFilter ? (
                        <button key={name} type="button" onClick={() => setBrandFilter(name)}
                          aria-pressed="false"
                          className={cn("rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                            "border-border bg-background text-muted-foreground",
                            "hover:border-primary/40 hover:bg-primary/5 hover:text-primary")}>
                          {name}<span className="ml-1 text-[10px] opacity-60">{count}</span>
                        </button>
                      ) : null
                    )}
                  </div>
                )}

                {/* Category chips */}
                {categories.length > 1 && (
                  <div role="group" aria-label="Filtrar por categoría" className="flex flex-wrap gap-1.5">
                    {categoryFilter && (
                      <button type="button" onClick={() => setCategoryFilter(null)}
                        aria-pressed="true"
                        className="rounded-full border border-secondary bg-secondary/10 px-3 py-1 text-xs font-medium text-secondary-foreground transition-colors hover:bg-secondary/20">
                        ✕ {categoryFilter}
                      </button>
                    )}
                    {categories.slice(0, 6).map(({ name, count }) =>
                      name && name !== categoryFilter ? (
                        <button key={name} type="button" onClick={() => setCategoryFilter(name)}
                          aria-pressed="false"
                          className={cn("rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                            "border-border/60 bg-muted text-muted-foreground",
                            "hover:border-secondary/40 hover:bg-secondary/5 hover:text-secondary-foreground")}>
                          {name}<span className="ml-1 text-[10px] opacity-60">{count}</span>
                        </button>
                      ) : null
                    )}
                  </div>
                )}

                {/* Price range */}
                {facetPriceMin != null && facetPriceMax != null && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>Precio:</span>
                    <input
                      type="number"
                      placeholder={`Mín ($${facetPriceMin.toLocaleString("es-CL")})`}
                      className="w-28 rounded-md border border-border bg-background px-2 py-1 text-xs"
                      value={priceRange ? priceRange[0] : ""}
                      onChange={(e) => {
                        const min = Number(e.target.value) || facetPriceMin;
                        setPriceRange([min, priceRange ? priceRange[1] : facetPriceMax]);
                      }}
                    />
                    <span>—</span>
                    <input
                      type="number"
                      placeholder={`Máx ($${facetPriceMax.toLocaleString("es-CL")})`}
                      className="w-28 rounded-md border border-border bg-background px-2 py-1 text-xs"
                      value={priceRange ? priceRange[1] : ""}
                      onChange={(e) => {
                        const max = Number(e.target.value) || facetPriceMax;
                        setPriceRange([priceRange ? priceRange[0] : facetPriceMin, max]);
                      }}
                    />
                    {priceRange && (
                      <button type="button" onClick={() => setPriceRange(null)}
                        className="text-xs text-muted-foreground hover:text-foreground">✕</button>
                    )}
                  </div>
                )}
              </div>
            )}

            <ProductGrid
              products={filteredSorted}
              isLoading={search.isFetching}
              emptyQuery={query}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
