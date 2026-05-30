"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/services/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";

interface ResetForm {
  new_password: string;
  confirm_password: string;
}

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") ?? "";

  const { register, handleSubmit, watch, formState: { errors } } = useForm<ResetForm>();

  const mutation = useMutation({
    mutationFn: (data: ResetForm) =>
      apiClient.resetPassword(token, data.new_password),
    onSuccess: () => {
      setTimeout(() => router.push("/"), 2000);
    },
  });

  if (!token) {
    return <Alert variant="destructive">Token inválido. Solicita un nuevo enlace de restablecimiento.</Alert>;
  }

  return (
    <div className="mx-auto max-w-sm p-6 space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Nueva contraseña</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
            <div>
              <Label htmlFor="new_password">Nueva contraseña</Label>
              <Input
                id="new_password"
                type="password"
                {...register("new_password", {
                  required: "Campo requerido",
                  minLength: { value: 12, message: "Mínimo 12 caracteres" },
                })}
              />
              {errors.new_password && (
                <p className="text-sm text-destructive mt-1">{errors.new_password.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="confirm_password">Confirmar contraseña</Label>
              <Input
                id="confirm_password"
                type="password"
                {...register("confirm_password", {
                  required: "Campo requerido",
                  validate: (v) => v === watch("new_password") || "Las contraseñas no coinciden",
                })}
              />
              {errors.confirm_password && (
                <p className="text-sm text-destructive mt-1">{errors.confirm_password.message}</p>
              )}
            </div>

            {mutation.isSuccess && (
              <Alert>Contraseña actualizada. Redirigiendo…</Alert>
            )}
            {mutation.isError && (
              <Alert variant="destructive">
                {(mutation.error as Error)?.message ?? "Error al restablecer contraseña."}
              </Alert>
            )}

            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? "Guardando…" : "Cambiar contraseña"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="p-6">Cargando…</div>}>
      <ResetPasswordContent />
    </Suspense>
  );
}
