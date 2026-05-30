"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/services/api-client";
import { useAppStore } from "@/stores/use-app-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";

interface ChangePasswordForm {
  current_password: string;
  new_password: string;
  confirm_new_password: string;
}

export default function ProfilePage() {
  const router = useRouter();
  const authUsername = useAppStore((s) => s.authUsername);

  useEffect(() => {
    if (!authUsername) {
      router.replace("/");
    }
  }, [authUsername, router]);

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiClient.getMe(),
    enabled: !!authUsername,
  });

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<ChangePasswordForm>();

  const mutation = useMutation({
    mutationFn: async (data: ChangePasswordForm) => {
      // TODO: wire to PATCH /auth/me once backend endpoint exists
      // Stub: simulate a successful password change
      console.log("Change password payload:", data);
      await new Promise((resolve) => setTimeout(resolve, 500));
    },
    onSuccess: () => {
      reset();
    },
  });

  if (!authUsername) return null;

  return (
    <div className="mx-auto max-w-lg p-6 space-y-6">
      <h1 className="text-2xl font-bold">Perfil</h1>

      <Card>
        <CardHeader>
          <CardTitle>Información de cuenta</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label>Usuario</Label>
            <Input value={user?.username ?? authUsername} readOnly className="bg-muted" />
          </div>
          <div>
            <Label>Email</Label>
            <Input value={user?.email ?? "—"} readOnly className="bg-muted" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cambiar contraseña</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
            <div>
              <Label htmlFor="current_password">Contraseña actual</Label>
              <Input
                id="current_password"
                type="password"
                {...register("current_password", { required: "Campo requerido" })}
              />
              {errors.current_password && (
                <p className="text-sm text-destructive mt-1">{errors.current_password.message}</p>
              )}
            </div>
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
              <Label htmlFor="confirm_new_password">Confirmar nueva contraseña</Label>
              <Input
                id="confirm_new_password"
                type="password"
                {...register("confirm_new_password", {
                  required: "Campo requerido",
                  validate: (v) => v === watch("new_password") || "Las contraseñas no coinciden",
                })}
              />
              {errors.confirm_new_password && (
                <p className="text-sm text-destructive mt-1">{errors.confirm_new_password.message}</p>
              )}
            </div>

            {mutation.isSuccess && (
              <Alert>Contraseña actualizada correctamente.</Alert>
            )}
            {mutation.isError && (
              <Alert variant="destructive">
                {(mutation.error as Error)?.message ?? "Error al cambiar contraseña."}
              </Alert>
            )}

            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Guardando…" : "Cambiar contraseña"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
