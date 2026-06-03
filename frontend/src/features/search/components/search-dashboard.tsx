"use client";

import { FormEvent, RefObject, useEffect, useMemo, useRef, useState } from "react";
import { Search, ShoppingBasket, Milk, Wheat, Wind, Coffee, Apple, Beef, ArrowDownNarrowWide, ArrowUpNarrowWide } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSearchProducts } from "@/hooks/use-search-products";
import { useAppStore } from "@/stores/use-app-store";
import { cn } from "@/lib/utils";
import { ProductGrid } from "./product-grid";
import { StoreTabs } from "@/components/layout/app-shell";

// ── Category quick-searches ────────────────────────────────────────────────

const CATEGORIES = [
  { label: "Leche",      icon: Milk,           q: "leche entera"   },
  { label: "Arroz",      icon: Wheat,          q: "arroz grado 2"  },
  { label: "Aceite",     icon: Coffee,         q: "aceite vegetal" },
  { label: "Detergente", icon: Wind,           q: "detergente"     },
  { label: "Fruta",      icon: Apple,          q: "manzana"        },
  { label: "Carne",      icon: Beef,           q: "pollo"          },
  { label: "Canasta",    icon: ShoppingBasket, q: "fideos"         },
];


// ── Rotating placeholders ──────────────────────────────────────────────────

const PLACEHOLDERS = [
  "leche entera 1 litro...",
  "arroz grano largo 1 kilo...",
  "detergente ropa...",
  "aceite maravilla...",
  "papel higiénico doble hoja...",
  "yogur frutilla...",
];

function useCyclingPlaceholder(strings: string[], ms = 2800) {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setIdx((i) => (i + 1) % strings.length), ms);
    return () => clearInterval(id);
  }, [strings, ms]);
  return strings[idx];
}

// Isolated so the cycling interval doesn't re-render the whole dashboard
function CyclingInput({
  inputRef,
  value,
  onChange,
}: {
  inputRef: RefObject<HTMLInputElement | null>;
  value: string;
  onChange: (v: string) => void;
}) {
  const placeholder = useCyclingPlaceholder(PLACEHOLDERS);
  return (
    <div className="relative flex-1">
      <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        ref={inputRef}
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          "h-12 w-full rounded-xl border border-border bg-[#f8f9fa] pl-10 pr-4",
          "text-sm text-foreground placeholder:text-muted-foreground",
          "focus:border-[#00913f] focus:outline-none focus:ring-2 focus:ring-[#00913f]/20",
          "transition-all duration-200"
        )}
      />
    </div>
  );
}

// ── Component ──────────────────────────────────────────────────────────────

export function SearchDashboard() {
  const activeStore     = useAppStore((s) => s.activeStore);
  const pushRecentQuery = useAppStore((s) => s.pushRecentQuery);
  const recentQueries   = useAppStore((s) => s.recentQueries);

  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  // Default to cheapest-first: that's what people comparing prices want.
  const [sortAsc, setSortAsc] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: searchResponse, isLoading, isError } = useSearchProducts(query, activeStore);
  const rawResults = searchResponse?.results ?? [];
  const searchWarning = searchResponse?.warning ?? null;

  // Sort by price (products with no/zero price sink to the bottom).
  const results = useMemo(() => {
    const withPrice = rawResults.filter((p) => p.price > 0);
    const noPrice = rawResults.filter((p) => !(p.price > 0));
    withPrice.sort((a, b) => (sortAsc ? a.price - b.price : b.price - a.price));
    return [...withPrice, ...noPrice];
  }, [rawResults, sortAsc]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = draft.trim();
    if (!q) return;
    pushRecentQuery(q);
    setQuery(q);
  }

  function fireQuery(q: string) {
    setDraft(q);
    pushRecentQuery(q);
    setQuery(q);
    inputRef.current?.focus();
  }

  const hasResults = results.length > 0;

  return (
    <div className="space-y-6">
      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="rounded-2xl bg-white px-6 py-8 shadow-sm sm:px-10 sm:py-10">
        <h1 className="text-center text-2xl font-bold leading-tight text-[#1a2332] sm:text-3xl md:text-4xl">
          Compara{" "}
          <span className="text-[#00913f]">Precios</span>{" "}
          y Encuentra
          <br />
          <span className="text-[#00913f]">Ofertas Reales</span> en Chile
        </h1>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Compara precios en Lider, Jumbo y Santa Isabel al mismo tiempo
        </p>

        {/* Search bar */}
        <form onSubmit={handleSubmit} className="mt-6 flex gap-2">
          <CyclingInput inputRef={inputRef} value={draft} onChange={setDraft} />
          <Button
            type="submit"
            className="h-12 rounded-xl px-6 text-sm font-semibold"
            style={{ background: "#00913f" }}
          >
            Buscar
          </Button>
        </form>

        {/* Store switcher */}
        <div className="mt-4 flex justify-center">
          <StoreTabs variant="light" />
        </div>

        {/* Recent queries */}
        {recentQueries.length > 0 && !query && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">Recientes:</span>
            {recentQueries.slice(0, 6).map((q) => (
              <button
                key={q}
                onClick={() => fireQuery(q)}
                className="rounded-full border border-border bg-[#f8f9fa] px-3 py-1 text-xs font-medium text-foreground transition-colors hover:border-[#00913f] hover:text-[#00913f]"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ── Category pills ─────────────────────────────────────── */}
      {!hasResults && !isLoading && !query && (
        <section className="flex flex-wrap gap-2">
          {CATEGORIES.map(({ label, icon: Icon, q }) => (
            <button
              key={label}
              onClick={() => fireQuery(q)}
              className="flex items-center gap-1.5 rounded-full border border-border bg-white px-3.5 py-2 text-sm font-medium text-foreground shadow-sm transition-all hover:border-[#00913f] hover:text-[#00913f]"
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </section>
      )}

      {/* ── Results ────────────────────────────────────────────── */}
      {(hasResults || isLoading || query) && (
        <section>
          {query && (
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-[#1a2332]">
                  {isLoading
                    ? `Buscando "${query}"...`
                    : `${results.length} resultado${results.length !== 1 ? "s" : ""} para "${query}"`}
                </h2>
                <p className="text-xs text-muted-foreground">
                  en {activeStore.replace("_", " ").toUpperCase()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {/* Sort by price toggle */}
                {hasResults && (
                  <button
                    onClick={() => setSortAsc((v) => !v)}
                    className="flex items-center gap-1 rounded-lg border border-border bg-white px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-[#00913f] hover:text-[#00913f]"
                    title={sortAsc ? "Mostrando del más barato al más caro" : "Mostrando del más caro al más barato"}
                  >
                    {sortAsc ? (
                      <ArrowUpNarrowWide className="h-3.5 w-3.5" />
                    ) : (
                      <ArrowDownNarrowWide className="h-3.5 w-3.5" />
                    )}
                    {sortAsc ? "Más barato" : "Más caro"}
                  </button>
                )}
                <button
                  onClick={() => { setQuery(""); setDraft(""); }}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Limpiar ✕
                </button>
              </div>
            </div>
          )}

          {/* Error / warning from scraper */}
          {(isError || searchWarning) && (
            <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {isError
                ? "⚠️ No se pudo conectar con la tienda. Verifica tu conexión e intenta de nuevo."
                : `⚠️ ${searchWarning}`}
            </div>
          )}

          <ProductGrid
            products={results}
            isLoading={isLoading}
            emptyQuery={!searchWarning ? query : undefined}
          />
        </section>
      )}
    </div>
  );
}
