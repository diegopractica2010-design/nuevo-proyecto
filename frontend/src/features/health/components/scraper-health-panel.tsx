"use client";

import { Activity, CircleAlert, CircleCheck, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useScraperHealth } from "@/hooks/use-scraper-health";
import { cn } from "@/lib/utils";

export function ScraperHealthPanel({ compact = false }: { compact?: boolean }) {
  const { data, isLoading } = useScraperHealth();
  const status = data?.status ?? "unknown";
  const ok = status === "ok";

  if (compact) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-xs">
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : ok ? <CircleCheck className="h-4 w-4 text-emerald-300" /> : <CircleAlert className="h-4 w-4 text-amber-300" />}
        <span className="hidden text-muted-foreground sm:inline">Scrapers</span>
        <Badge variant={ok ? "success" : "warning"}>{status}</Badge>
      </div>
    );
  }

  return (
    <Card id="insights" className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Scraper health
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {Object.entries(data?.stores ?? {}).map(([store, entry]) => (
          <div key={store} className="flex items-center justify-between gap-3 rounded-md border border-white/10 bg-black/20 p-3">
            <div>
              <p className="text-sm font-medium capitalize">{store}</p>
              <p className="text-xs text-muted-foreground">{entry.parse_strategy ?? "waiting for monitor"}</p>
            </div>
            <Badge
              variant={entry.status === "ok" ? "success" : entry.status === "down" ? "destructive" : "warning"}
              className={cn("capitalize")}
            >
              {entry.status}
            </Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
