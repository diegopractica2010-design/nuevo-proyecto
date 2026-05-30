"use client";

import { Suspense, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppLayout } from "@/layouts/app-layout";
import { apiClient } from "@/services/api-client";

const SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?";

function passwordIssues(password: string): string[] {
  const issues: string[] = [];
  if (password.length < 12) issues.push("Debe tener al menos 12 caracteres.");
  if (password.length > 128) issues.push("No puede exceder 128 caracteres.");
  if (!/[A-Z]/.test(password)) issues.push("Debe incluir una mayúscula.");
  if (!/\d/.test(password)) issues.push("Debe incluir un número.");
  if (![...password].some((char) => SPECIAL_CHARS.includes(char))) {
    issues.push("Debe incluir un carácter especial.");
  }
  return issues;
}

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const issues = useMemo(() => passwordIssues(password), [password]);
  const passwordsMatch = password === confirmPassword;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!token) {
      setError("El enlace de recuperación no incluye un token válido.");
      return;
    }
    if (issues.length > 0) {
      setError(issues.join(" "));
      return;
    }
    if (!passwordsMatch) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await apiClient.resetPassword(token, password);
      setSuccess(response.detail);
      setPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar la contraseña.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-xl py-12">
        <Card>
          <CardHeader>
            <CardTitle>Restablecer contraseña</CardTitle>
            <CardDescription>Ingresa una nueva contraseña segura para tu cuenta.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={handleSubmit}>
              {!token ? (
                <Alert>
                  <AlertTitle>Token faltante</AlertTitle>
                  <AlertDescription>Solicita un nuevo enlace de recuperación.</AlertDescription>
                </Alert>
              ) : null}

              <div className="space-y-2">
                <Label htmlFor="new-password">Nueva contraseña</Label>
                <Input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirmar contraseña</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  required
                />
              </div>

              {password && issues.length > 0 ? (
                <Alert>
                  <AlertTitle>La contraseña aún no cumple la política</AlertTitle>
                  <AlertDescription>{issues.join(" ")}</AlertDescription>
                </Alert>
              ) : null}

              {confirmPassword && !passwordsMatch ? (
                <Alert>
                  <AlertTitle>Confirmación inválida</AlertTitle>
                  <AlertDescription>Las contraseñas no coinciden.</AlertDescription>
                </Alert>
              ) : null}

              {error ? (
                <Alert>
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}

              {success ? (
                <Alert>
                  <AlertTitle>Contraseña actualizada</AlertTitle>
                  <AlertDescription>{success}</AlertDescription>
                </Alert>
              ) : null}

              <Button type="submit" className="w-full" disabled={isSubmitting || !token}>
                {isSubmitting ? "Actualizando..." : "Actualizar contraseña"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}
