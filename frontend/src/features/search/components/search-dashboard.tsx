"use client";

import { FormEvent, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Search, Sparkles, TrendingDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSearchProducts } from "@/hooks/use-search-products";
import { formatCurrency } from "@/lib/utils";
import { useAppStore } from "@/stores/use-app-store";
import { ProductGrid } from "./product-grid";
import { StoreSwitcher } from "./store-switcher";

const quickQueries = ["arroz 1 kilo", "leche entera 1 litro", "aceite 1 litro", "detergente ropa"];

export function SearchDashboard() {
  const activeStore = useAppStore((state) => state.activeStore);
  const setActiveStore = useAppStore((state) => state.setActiveStore);
  const pushRecentQuery = useAppStore((state) => state.pushRecentQuery);
  const recentQueries = useAppStore((state) => state.recentQueries);
  const [draft, setDraft] = useState("arroz 1 kilo");
  const [query, setQuery] = useState("arroz 1 kilo");
  const search = useSearchProducts(query, activeStore);

  const cheapest = useMemo(
    () => search.data?.results.reduce((best, item) => (!best || item.price < best.price ? item : best), search.data.results[0]),
    [search.data]
  );

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuery = draft.trim();
    if (!nextQuery) return;
    setQuery(nextQuery);
    pushRecentQuery(nextQuery);
  }

  return (
    <section id="search" className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="space-y-6">
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-white/10">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-2xl">
                <Badge variant="secondary" className="mb-3">Live market intelligence</Badge>
                <CardTitle className="text-3xl font-semibold tracking-normal sm:text-4xl">
                  Compara precios reales con una experiencia de control ejecutivo.
                </CardTitle>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Búsqueda live, cache DB, salud de scrapers y comparación por precio unitario en una interfaz rápida.
                </p>
              </div>
              <StoreSwitcher value={activeStore} onChange={setActiveStore} />
            </div>
          </CardHeader>
          <CardContent className="p-5">
            <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  className="pl-9"
                  placeholder="Busca leche, arroz, café, detergente..."
                />
              </div>
              <Button type="submit" size="lg">
                <Sparkles className="h-4 w-4" />
                Buscar
              </Button>
            </form>
            <div className="mt-4 flex flex-wrap gap-2">
              {quickQueries.map((item) => (
                <Button key={item} type="button" variant="outline" size="sm" onClick={() => { setDraft(item); setQuery(item); pushRecentQuery(item); }}>
                  {item}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        <ProductGrid products={search.data?.results ?? []} isLoading={search.isFetching} />
      </div>

      <aside className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-primary" />
              Market snapshot
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Metric label="Resultados" value={String(search.data?.count ?? 0)} />
            <Metric label="Mejor precio" value={formatCurrency(cheapest?.price)} />
            <Metric label="Promedio" value={formatCurrency(search.data?.stats.average_price)} />
            <Metric label="Estrategia" value={search.data?.strategy ?? "waiting"} small />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent demand</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {recentQueries.map((item) => (
              <button
                key={item}
                className="rounded-md border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-xs text-muted-foreground transition hover:text-foreground"
                onClick={() => { setDraft(item); setQuery(item); }}
              >
                {item}
              </button>
            ))}
          </CardContent>
        </Card>

        {search.data?.warning ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <Card className="border-amber-300/20 bg-amber-300/8">
              <CardContent className="p-4 text-sm text-amber-100">{search.data.warning}</CardContent>
            </Card>
          </motion.div>
        ) : null}
      </aside>
    </section>
  );
}

function Metric({ label, value, small = false }: { label: string; value: string; small?: boolean }) {
  return (
    <div className="rounded-md border border-white/10 bg-black/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={small ? "mt-1 truncate text-xs font-medium" : "mt-1 text-xl font-semibold"}>{value}</p>
    </div>
  );
}
