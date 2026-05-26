"use client";

import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { apiClient } from "@/services/api-client";
import type { StoreId } from "@/types/api";
import { formatCurrency } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

interface Props {
  product_id: string;
  store: StoreId;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

export function PriceHistoryChart({ product_id, store }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["price-history", product_id, store],
    queryFn: () => apiClient.getPriceHistory(product_id, store),
    staleTime: 5 * 60 * 1000
  });

  if (isLoading) {
    return <Skeleton className="h-28 w-full rounded-lg" />;
  }

  if (isError || !data) {
    return (
      <p className="text-xs text-muted-foreground py-2 text-center">
        No se pudo cargar el historial de precios.
      </p>
    );
  }

  const history = data.history ?? [];

  if (history.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2 text-center">
        Sin historial de precios disponible.
      </p>
    );
  }

  const chartData = history.map((point) => ({
    date: formatDate(point.date),
    price: point.price
  }));

  const { trends } = data;

  return (
    <div className="space-y-2 pt-1">
      {trends && (
        <div className="flex gap-4 text-xs text-muted-foreground">
          {trends.min_price != null && (
            <span>Min: <span className="text-foreground font-medium">{formatCurrency(trends.min_price)}</span></span>
          )}
          {trends.max_price != null && (
            <span>Max: <span className="text-foreground font-medium">{formatCurrency(trends.max_price)}</span></span>
          )}
          {trends.trend && (
            <span className="ml-auto capitalize">{trends.trend}</span>
          )}
        </div>
      )}
      <ResponsiveContainer width="100%" height={96}>
        <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} />
          <YAxis
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            width={36}
          />
          <Tooltip
            formatter={(value: number) => [formatCurrency(value), "Precio"]}
            contentStyle={{
              background: "hsl(var(--background))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "6px",
              fontSize: 12
            }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
