"use client";

import { BarChart3, Command, LineChart, Radar, ShoppingBasket } from "lucide-react";
import { motion } from "framer-motion";
import { ScraperHealthPanel } from "@/features/health/components/scraper-health-panel";
import { cn } from "@/lib/utils";

const navigation = [
  { label: "Search", icon: Command, href: "#search" },
  { label: "Compare", icon: ShoppingBasket, href: "#compare" },
  { label: "Insights", icon: LineChart, href: "#insights" }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-20 border-r border-white/10 bg-black/30 backdrop-blur-xl lg:flex lg:flex-col lg:items-center lg:py-5">
        <a className="mb-8 flex h-11 w-11 items-center justify-center rounded-lg bg-primary text-primary-foreground" href="#">
          <Radar className="h-5 w-5" />
        </a>
        <nav className="flex flex-1 flex-col gap-3">
          {navigation.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-white/8 hover:text-foreground"
              aria-label={item.label}
            >
              <item.icon className="h-5 w-5" />
            </a>
          ))}
        </nav>
        <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-white/10 text-muted-foreground">
          <BarChart3 className="h-5 w-5" />
        </div>
      </aside>

      <main className="lg:pl-20">
        <header className="sticky top-0 z-30 border-b border-white/10 bg-background/78 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground lg:hidden">
                <Radar className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold">Radar de Precios</p>
                <p className="truncate text-xs text-muted-foreground">Enterprise grocery intelligence</p>
              </div>
            </div>
            <ScraperHealthPanel compact />
          </div>
        </header>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
          className={cn("mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8")}
        >
          {children}
        </motion.div>
      </main>
    </div>
  );
}
