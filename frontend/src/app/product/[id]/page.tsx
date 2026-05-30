"use client";

import { Suspense } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/api-client";
import type { StoreId } from "@/types/api";
import { PriceHistoryChart } from "@/features/search/components/price-history-chart";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function ProductDetailContent() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const store = (searchParams.get("store") ?? "lider") as StoreId;
  const productId = decodeURIComponent(params.id);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["price-history", productId, store],
    queryFn: () => apiClient.getPriceHistory(productId, store),
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6 space-y-4">
        <Button variant="outline" onClick={() => router.back()}>← Volver</Button>
        <Alert variant="destructive">
          <p>{(error as Error)?.message ?? "No se pudo cargar el historial de precios."}</p>
          <Button size="sm" className="mt-2" onClick={() => refetch()}>Reintentar</Button>
        </Alert>
      </div>
    );
  }

  const trends = data?.trends;
  const history = data?.history ?? [];

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <Button variant="outline" onClick={() => router.back()}>← Volver a la búsqueda</Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">
            {history[0]?.store ? `${store.toUpperCase()} — ` : ""}
            Historial de precios
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {trends && (
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-sm text-muted-foreground">Precio actual</p>
                <p className="text-lg font-bold">
                  {trends.current_price != null ? `$${trends.current_price.toLocaleString("es-CL")}` : "—"}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Mínimo</p>
                <p className="text-lg font-semibold text-green-600">
                  {trends.min_price != null ? `$${trends.min_price.toLocaleString("es-CL")}` : "—"}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Máximo</p>
                <p className="text-lg font-semibold text-red-500">
                  {trends.max_price != null ? `$${trends.max_price.toLocaleString("es-CL")}` : "—"}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {history.length > 0 ? (
        <PriceHistoryChart history={history} />
      ) : (
        <Alert>
          <p>No hay registros de historial para este producto aún.</p>
        </Alert>
      )}
    </div>
  );
}

export default function ProductDetailPage() {
  return (
    <Suspense fallback={
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    }>
      <ProductDetailContent />
    </Suspense>
  );
}
