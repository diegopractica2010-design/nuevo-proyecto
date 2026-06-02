"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LogOut, Moon, ShoppingCart, Sun, User } from "lucide-react";
import { AuthModal } from "@/features/auth/components/auth-modal";
import { cn } from "@/lib/utils";
import { apiClient } from "@/services/api-client";
import { useAppStore } from "@/stores/use-app-store";
import type { StoreId, StoreInfo } from "@/types/api";

// ── All known stores (fallback while API loads) ────────────────────────────

const FALLBACK_STORES: StoreInfo[] = [
  { id: "lider",        display_name: "Lider",        experimental: false },
  { id: "jumbo",        display_name: "Jumbo",        experimental: false },
  { id: "santa_isabel", display_name: "Santa Isabel", experimental: true  },
  { id: "acuenta",      display_name: "Acuenta",      experimental: true  },
  { id: "tottus",       display_name: "Tottus",       experimental: true  },
  { id: "unimarc",      display_name: "Unimarc",      experimental: true  },
];

// ── Store color accents ────────────────────────────────────────────────────

const STORE_COLORS: Record<string, string> = {
  lider:        "#00913f",
  jumbo:        "#e5002b",
  santa_isabel: "#e5002b",
  acuenta:      "#f6a800",
  tottus:       "#e5002b",
  unimarc:      "#003da5",
};

// ── Radar wordmark ─────────────────────────────────────────────────────────

function RadarWordmark() {
  return (
    <Link href="/" className="flex items-center gap-2 select-none shrink-0">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#00913f]">
        <svg className="h-5 w-5 text-white" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19.07 4.93A10 10 0 0 0 6.99 3.34" />
          <path d="M2.29 9.62A10 10 0 1 0 21.31 8.35" />
          <path d="M16.24 7.76A6 6 0 1 0 8.23 16.67" />
          <circle cx="12" cy="12" r="2" />
          <path d="m13.41 10.59 5.66-5.66" />
        </svg>
      </div>
      <div className="hidden sm:block">
        <span className="text-base font-bold tracking-tight text-white">Radar</span>
        <span className="ml-1 text-xs text-white/60">de Precios</span>
      </div>
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
      className="flex h-8 w-8 items-center justify-center rounded-lg text-white/70 transition-colors hover:bg-white/10 hover:text-white"
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}

// ── Store tabs (in header) ─────────────────────────────────────────────────

export function StoreTabs() {
  const activeStore = useAppStore((s) => s.activeStore);
  const setActiveStore = useAppStore((s) => s.setActiveStore);
  const { data: stores = FALLBACK_STORES } = useQuery({
    queryKey: ["stores"],
    queryFn: () => apiClient.getStores(),
    staleTime: 5 * 60 * 1000,   // 5 min (not Infinity, so it retries)
    retry: 3,
  });

  return (
    <div className="flex items-center gap-0.5 overflow-x-auto scrollbar-none">
      {stores.map((s) => {
        const active = activeStore === s.id;
        const color = STORE_COLORS[s.id] ?? "#00913f";
        return (
          <button
            key={s.id}
            onClick={() => setActiveStore(s.id as StoreId)}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all duration-150",
              active
                ? "bg-white text-[#1a2332] shadow-sm"
                : "text-white/70 hover:bg-white/10 hover:text-white"
            )}
            style={active ? { color: color } : undefined}
          >
            {/* Color dot */}
            <span
              className="inline-block h-2 w-2 rounded-full shrink-0"
              style={{ background: color }}
            />
            {s.display_name}
          </button>
        );
      })}
    </div>
  );
}

// ── Shell ──────────────────────────────────────────────────────────────────

export function AppShell({ children }: { children: React.ReactNode }) {
  const authUsername = useAppStore((s) => s.authUsername);
  const authToken    = useAppStore((s) => s.authToken);
  const logout       = useAppStore((s) => s.logout);
  const cartCount    = useAppStore((s) => s.cartCount);

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiClient.getMe(),
    enabled: !!authToken,
    staleTime: 300_000,
  });
  const isAdmin = (me as (typeof me & { role?: string }) | undefined)?.role === "admin";

  return (
    <div className="flex min-h-screen flex-col bg-[#f2f3f5]">
      {/* ── Header — dark navy ─────────────────────────────────── */}
      <header
        role="banner"
        className="sticky top-0 z-40 shadow-md"
        style={{ background: "#1a2332" }}
      >
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 sm:px-6">
          <RadarWordmark />

          {/* Store tabs — center */}
          <div className="hidden flex-1 justify-center md:flex">
            <StoreTabs />
          </div>

          {/* Right actions */}
          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />

            {cartCount > 0 && (
              <Link
                href="/baskets"
                className="relative flex h-8 w-8 items-center justify-center rounded-lg text-white/70 transition-colors hover:bg-white/10 hover:text-white"
              >
                <ShoppingCart className="h-4 w-4" />
                <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[#00913f] text-[9px] font-bold text-white">
                  {cartCount > 9 ? "9+" : cartCount}
                </span>
              </Link>
            )}

            {authUsername ? (
              <div className="flex items-center gap-1">
                {isAdmin && (
                  <Link
                    href="/admin"
                    className="hidden rounded-md px-2 py-1 text-xs font-medium text-white/60 hover:bg-white/10 hover:text-white sm:inline"
                  >
                    Admin
                  </Link>
                )}
                <Link
                  href="/profile"
                  className="hidden items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-white/80 hover:bg-white/10 hover:text-white sm:flex"
                >
                  <User className="h-3 w-3" />
                  <span className="max-w-[80px] truncate">{authUsername}</span>
                </Link>
                <button
                  onClick={logout}
                  aria-label="Cerrar sesión"
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-white/70 transition-colors hover:bg-white/10 hover:text-white"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <AuthModal
                trigger={
                  <button className="rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-white/20">
                    Ingresar
                  </button>
                }
              />
            )}
          </div>
        </div>

        {/* Mobile store tabs */}
        <div className="border-t border-white/10 px-4 py-2 md:hidden">
          <StoreTabs />
        </div>
      </header>

      {/* ── Content ── */}
      <main role="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        {children}
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-border bg-white py-6 text-center text-xs text-muted-foreground">
        <p className="font-medium text-[#1a2332]">Radar de Precios</p>
        <p className="mt-1">Santiago, Chile · Precios actualizados en tiempo real</p>
      </footer>
    </div>
  );
}
