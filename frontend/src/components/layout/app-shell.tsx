"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LogOut, Moon, ShoppingCart, Sun } from "lucide-react";
import { AuthModal } from "@/features/auth/components/auth-modal";
import { cn } from "@/lib/utils";
import { apiClient } from "@/services/api-client";
import { useAppStore } from "@/stores/use-app-store";
import type { StoreId, StoreInfo } from "@/types/api";

// ── SVG store logos ────────────────────────────────────────────────────────

function LiderLogo({ active }: { active: boolean }) {
  return (
    <svg width="32" height="16" viewBox="0 0 32 16" fill="none" aria-hidden>
      <rect width="32" height="16" rx="3" fill={active ? "#00913f" : "transparent"} />
      <text x="16" y="12" textAnchor="middle"
        fill={active ? "#fff" : "#00913f"}
        fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700">
        LIDER
      </text>
    </svg>
  );
}

function JumboLogo({ active }: { active: boolean }) {
  return (
    <svg width="32" height="16" viewBox="0 0 32 16" fill="none" aria-hidden>
      <rect width="32" height="16" rx="3" fill={active ? "#e5002b" : "transparent"} />
      <text x="16" y="12" textAnchor="middle"
        fill={active ? "#fff" : "#e5002b"}
        fontFamily="system-ui,sans-serif" fontSize="9" fontWeight="700">
        JUMBO
      </text>
    </svg>
  );
}

function StoreLogoFor({ id, active }: { id: string; active: boolean }) {
  if (id === "lider") return <LiderLogo active={active} />;
  if (id === "jumbo") return <JumboLogo active={active} />;
  return <span className="text-xs font-semibold uppercase">{id}</span>;
}

// ── Radar wordmark ─────────────────────────────────────────────────────────

function RadarWordmark() {
  return (
    <Link href="/" className="flex items-center gap-2 select-none">
      <svg className="h-5 w-5 text-primary" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19.07 4.93A10 10 0 0 0 6.99 3.34" />
        <path d="M2.29 9.62A10 10 0 1 0 21.31 8.35" />
        <path d="M16.24 7.76A6 6 0 1 0 8.23 16.67" />
        <circle cx="12" cy="12" r="2" />
        <path d="m13.41 10.59 5.66-5.66" />
      </svg>
      <span className="text-[15px] font-bold tracking-tight">Radar</span>
    </Link>
  );
}

// ── Theme toggle ───────────────────────────────────────────────────────────

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);
  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }
  return (
    <button
      onClick={toggle}
      aria-label="Cambiar tema"
      className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}

// ── Store tab switcher ─────────────────────────────────────────────────────

const FALLBACK_STORES: StoreInfo[] = [
  { id: "lider", display_name: "Lider", experimental: false },
  { id: "jumbo", display_name: "Jumbo", experimental: true },
];

function StoreTabs() {
  const activeStore = useAppStore((s) => s.activeStore);
  const setActiveStore = useAppStore((s) => s.setActiveStore);
  const { data: stores = FALLBACK_STORES } = useQuery({
    queryKey: ["stores"],
    queryFn: () => apiClient.getStores(),
    staleTime: Infinity,
  });

  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-border bg-muted p-0.5">
      {stores.map((s) => {
        const active = activeStore === s.id;
        return (
          <button
            key={s.id}
            onClick={() => setActiveStore(s.id as StoreId)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all duration-200",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <StoreLogoFor id={s.id} active={active} />
          </button>
        );
      })}
    </div>
  );
}

// ── Shell ──────────────────────────────────────────────────────────────────

export function AppShell({ children }: { children: React.ReactNode }) {
  const authUsername = useAppStore((s) => s.authUsername);
  const logout = useAppStore((s) => s.logout);
  const cartCount = useAppStore((s) => s.cartCount);

  return (
    <div className="flex min-h-screen flex-col">
      {/* ── Header ── */}
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3 sm:px-6">
          <RadarWordmark />

          <div className="flex flex-1 justify-center">
            <StoreTabs />
          </div>

          <div className="flex items-center gap-1.5">
            <ThemeToggle />

            {cartCount > 0 && (
              <Link
                href="/baskets"
                className="relative flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              >
                <ShoppingCart className="h-4 w-4" />
                <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-primary-foreground">
                  {cartCount > 9 ? "9+" : cartCount}
                </span>
              </Link>
            )}

            {authUsername ? (
              <div className="flex items-center gap-2">
                <span className="hidden max-w-[100px] truncate text-xs text-muted-foreground sm:inline">
                  {authUsername}
                </span>
                <button
                  onClick={logout}
                  aria-label="Cerrar sesión"
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <AuthModal
                trigger={
                  <button className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent">
                    Ingresar
                  </button>
                }
              />
            )}
          </div>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        {children}
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-border/60 py-5 text-center text-xs text-muted-foreground">
        Radar de Precios · Santiago, Chile · Precios actualizados en tiempo real
      </footer>
    </div>
  );
}
