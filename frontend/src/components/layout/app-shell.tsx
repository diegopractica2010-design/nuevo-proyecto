"use client";

import { BarChart3, Command, LineChart, LogOut, Menu, Radar, Settings, ShoppingBasket, User, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ScraperHealthPanel } from "@/features/health/components/scraper-health-panel";
import { AuthModal } from "@/features/auth/components/auth-modal";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/stores/use-app-store";
import { cn } from "@/lib/utils";
import { useState } from "react";

const navigation = [
  { label: "Search", icon: Command, href: "#search" },
  { label: "Compare", icon: ShoppingBasket, href: "#compare" },
  { label: "Insights", icon: LineChart, href: "#insights" }
];

const userMenu = [
  { label: "Profile", icon: User },
  { label: "Settings", icon: Settings },
  { label: "Logout", icon: LogOut, variant: "destructive" as const }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const authUsername = useAppStore((s) => s.authUsername);
  const logout = useAppStore((s) => s.logout);

  return (
    <div className="min-h-screen">
      {/* Sidebar - Desktop */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-20 border-r border-white/10 bg-black/30 backdrop-blur-xl lg:flex lg:flex-col lg:items-center lg:py-5">
        <a className="mb-8 flex h-11 w-11 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors" href="#/">
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
        <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-white/10 text-muted-foreground hover:bg-white/8 transition-colors cursor-pointer">
          <BarChart3 className="h-5 w-5" />
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:pl-20">
        {/* Header */}
        <header className="sticky top-0 z-30 border-b border-white/10 bg-background/78 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground lg:hidden">
                <Radar className="h-5 w-5" />
              </div>
              <div className="min-w-0 hidden sm:block">
                <p className="text-sm font-semibold">Radar de Precios</p>
                <p className="truncate text-xs text-muted-foreground">Enterprise grocery intelligence</p>
              </div>
            </div>

            <div className="flex items-center gap-4 ml-auto">
              <div className="hidden md:flex">
                <ScraperHealthPanel compact />
              </div>

              {/* Auth */}
              {authUsername ? (
                <div className="flex items-center gap-2">
                  <span className="hidden sm:flex items-center gap-1.5 text-sm text-muted-foreground">
                    <User className="h-3.5 w-3.5" />
                    {authUsername}
                  </span>
                  <Button variant="ghost" size="sm" onClick={logout} aria-label="Logout">
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <AuthModal />
              )}

              {/* Mobile Menu Button */}
              <button
                className="lg:hidden p-2 hover:bg-white/8 rounded-lg transition-colors"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>

          {/* Mobile Menu */}
          <AnimatePresence>
            {mobileMenuOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="border-t border-white/10 bg-black/30 backdrop-blur-xl lg:hidden"
              >
                <nav className="flex gap-2 p-4">
                  {navigation.map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-white/8 hover:text-foreground transition"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </a>
                  ))}
                </nav>
              </motion.div>
            )}
          </AnimatePresence>
        </header>

        {/* Content */}
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
