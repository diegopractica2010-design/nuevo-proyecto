"use client";

import { useState } from "react";
import { Lock, Loader2, Mail, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { apiClient } from "@/services/api-client";
import { useAppStore } from "@/stores/use-app-store";

// ── Icon input ─────────────────────────────────────────────────────────────

function IconInput({
  id,
  icon: Icon,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  icon: typeof User;
}) {
  return (
    <div className="relative">
      <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input id={id} className="pl-9" {...props} />
    </div>
  );
}

// ── Radar logo for modal ───────────────────────────────────────────────────

function ModalLogo() {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
        <svg className="h-5 w-5 text-primary" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19.07 4.93A10 10 0 0 0 6.99 3.34" />
          <path d="M2.29 9.62A10 10 0 1 0 21.31 8.35" />
          <path d="M16.24 7.76A6 6 0 1 0 8.23 16.67" />
          <circle cx="12" cy="12" r="2" />
          <path d="m13.41 10.59 5.66-5.66" />
        </svg>
      </div>
      <p className="text-[13px] font-semibold text-foreground">Radar de Precios</p>
    </div>
  );
}

// ── Modal ──────────────────────────────────────────────────────────────────

export function AuthModal({ trigger }: { trigger?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const setAuth = useAppStore((s) => s.setAuth);

  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [regForm, setRegForm] = useState({ username: "", email: "", password: "" });

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await apiClient.login(loginForm);
      setAuth(token.access_token, loginForm.username);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Credenciales incorrectas");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiClient.register(regForm);
      const token = await apiClient.login({ username: regForm.username, password: regForm.password });
      setAuth(token.access_token, regForm.username);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la cuenta");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); setError(null); }}>
      <DialogTrigger asChild>
        {trigger ?? (
          <button className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent">
            Ingresar
          </button>
        )}
      </DialogTrigger>

      <DialogContent className="sm:max-w-sm">
        <div className="flex flex-col gap-5">
          <ModalLogo />

          <Tabs defaultValue="login" onValueChange={() => setError(null)} className="w-full">
            <TabsList className="w-full">
              <TabsTrigger value="login" className="flex-1">Ingresar</TabsTrigger>
              <TabsTrigger value="register" className="flex-1">Crear cuenta</TabsTrigger>
            </TabsList>

            {/* Login */}
            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-3 pt-1">
                <div className="space-y-1">
                  <Label htmlFor="login-user" className="text-xs">Usuario</Label>
                  <IconInput
                    id="login-user"
                    icon={User}
                    autoComplete="username"
                    value={loginForm.username}
                    onChange={(e) => setLoginForm((f) => ({ ...f, username: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="login-pass" className="text-xs">Contraseña</Label>
                  <IconInput
                    id="login-pass"
                    icon={Lock}
                    type="password"
                    autoComplete="current-password"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm((f) => ({ ...f, password: e.target.value }))}
                    required
                  />
                </div>
                {error && <p className="text-xs text-destructive">{error}</p>}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {loading ? "Ingresando…" : "Ingresar"}
                </Button>
              </form>
            </TabsContent>

            {/* Register */}
            <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-3 pt-1">
                <div className="space-y-1">
                  <Label htmlFor="reg-user" className="text-xs">Usuario</Label>
                  <IconInput
                    id="reg-user"
                    icon={User}
                    autoComplete="username"
                    value={regForm.username}
                    onChange={(e) => setRegForm((f) => ({ ...f, username: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="reg-email" className="text-xs">Correo</Label>
                  <IconInput
                    id="reg-email"
                    icon={Mail}
                    type="email"
                    autoComplete="email"
                    value={regForm.email}
                    onChange={(e) => setRegForm((f) => ({ ...f, email: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="reg-pass" className="text-xs">Contraseña</Label>
                  <IconInput
                    id="reg-pass"
                    icon={Lock}
                    type="password"
                    autoComplete="new-password"
                    value={regForm.password}
                    onChange={(e) => setRegForm((f) => ({ ...f, password: e.target.value }))}
                    required
                  />
                </div>
                {error && <p className="text-xs text-destructive">{error}</p>}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {loading ? "Creando cuenta…" : "Crear cuenta"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
}
