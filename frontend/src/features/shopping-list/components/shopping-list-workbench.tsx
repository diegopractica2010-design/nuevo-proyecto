"use client";

import { FormEvent, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowDownUp, CheckCircle2, Loader2, ShieldQuestion, ShoppingBasket } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useShoppingListCompare } from "@/hooks/use-shopping-list";
import { formatCurrency } from "@/lib/utils";

const starterList = `arroz 1 kilo
leche entera 1 litro
aceite 1 litro
detergente ropa
papel higienico`;

export function ShoppingListWorkbench() {
  const [value, setValue] = useState(starterList);
  const compare = useShoppingListCompare();
  const items = useMemo(
    () => value.split("\n").map((item) => item.trim()).filter(Boolean).slice(0, 40),
    [value]
  );

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (items.length) compare.mutate(items);
  }

  return (
    <section id="compare" className="grid gap-6 xl:grid-cols-[26rem_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <Badge variant="secondary" className="w-fit">Cross-store matching</Badge>
          <CardTitle className="flex items-center gap-2 text-2xl">
            <ShoppingBasket className="h-5 w-5 text-primary" />
            Lista de compras
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <Textarea value={value} onChange={(event) => setValue(event.target.value)} />
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">{items.length} items preparados</p>
              <Button type="submit" disabled={compare.isPending || !items.length}>
                {compare.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowDownUp className="h-4 w-4" />}
                Comparar
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="min-h-96">
        <CardHeader className="border-b border-white/10">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Resultado operativo</CardTitle>
            <div className="text-sm text-muted-foreground">
              {compare.data ? `${compare.data.matched_count}/${compare.data.count} encontrados` : "Esperando lista"}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 p-4">
          {compare.isPending ? (
            <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Calculando mejor canasta
            </div>
          ) : null}

          {compare.data ? (
            <>
              <div className="rounded-lg border border-primary/20 bg-primary/8 p-4">
                <p className="text-xs text-muted-foreground">Total estimado</p>
                <p className="text-3xl font-semibold">{formatCurrency(compare.data.estimated_total)}</p>
              </div>
              {compare.data.items.map((item) => (
                <motion.div
                  key={item.query}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-lg border border-white/10 bg-black/20 p-4"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <p className="font-medium">{item.query}</p>
                      <div className="mt-1 flex flex-wrap gap-2">
                        <Badge variant={item.same_product ? "success" : "warning"}>
                          {item.same_product ? <CheckCircle2 className="mr-1 h-3 w-3" /> : <ShieldQuestion className="mr-1 h-3 w-3" />}
                          {item.same_product ? "Mismo producto" : "Match incierto"}
                        </Badge>
                        {item.cheapest?.unit_price ? <Badge variant="secondary">{item.cheapest.unit_price}</Badge> : null}
                      </div>
                    </div>
                    <p className="text-lg font-semibold">{formatCurrency(item.cheapest?.price)}</p>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {item.stores.map((store) => (
                      <div key={store.store} className="rounded-md border border-white/10 bg-white/[0.035] p-3">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-medium uppercase text-muted-foreground">{store.store}</p>
                          {store.error ? <Badge variant="destructive">Sin datos</Badge> : null}
                        </div>
                        <p className="mt-1 line-clamp-2 text-sm">{store.best?.name ?? "No encontrado"}</p>
                        <p className="mt-2 text-sm font-semibold">{formatCurrency(store.best?.price)}</p>
                      </div>
                    ))}
                  </div>
                </motion.div>
              ))}
            </>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
