"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/services/api-client";
import { useAppStore } from "@/stores/use-app-store";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";
import { ScraperHealthPanel } from "@/features/health/components/scraper-health-panel";
import { Spinner } from "@/components/ui/spinner";

export default function AdminPage() {
  const router = useRouter();
  const authToken = useAppStore((s) => s.authToken);
  const authUsername = useAppStore((s) => s.authUsername);
  const queryClient = useQueryClient();

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiClient.getMe(),
    enabled: !!authToken,
  });

  useEffect(() => {
    if (!authUsername) {
      router.replace("/");
    }
  }, [authUsername, router]);

  // ── Backup tab ─────────────────────────────────────────────────────────────

  const { data: backupStatus, refetch: refetchBackup } = useQuery({
    queryKey: ["backup-status"],
    queryFn: () => apiClient.getBackupStatus(),
    refetchInterval: 30000,
  });

  const backupMutation = useMutation({
    mutationFn: () => apiClient.triggerBackup(),
    onSuccess: () => {
      setTimeout(() => refetchBackup(), 2000);
    },
  });

  // ── Users tab ──────────────────────────────────────────────────────────────

  const [promoteUsername, setPromoteUsername] = useState("");
  const [promoteRole, setPromoteRole] = useState("admin");

  const promoteMutation = useMutation({
    mutationFn: ({ username, role }: { username: string; role: string }) =>
      apiClient.promoteUser(username, role),
    onSuccess: () => {
      setPromoteUsername("");
    },
  });

  // ── Scrapers tab ───────────────────────────────────────────────────────────

  const forceCheckMutation = useMutation({
    mutationFn: () => apiClient.forceParserCheck(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scraper-health"] });
    },
  });

  if (!authUsername) return null;

  return (
    <div className="mx-auto max-w-4xl p-6 space-y-6">
      <h1 className="text-2xl font-bold">Panel de Administración</h1>

      <Tabs defaultValue="scrapers">
        <TabsList>
          <TabsTrigger value="scrapers">Scrapers</TabsTrigger>
          <TabsTrigger value="backups">Backups</TabsTrigger>
          <TabsTrigger value="users">Usuarios</TabsTrigger>
        </TabsList>

        {/* ── SCRAPERS TAB ── */}
        <TabsContent value="scrapers" className="space-y-4">
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => forceCheckMutation.mutate()}
              disabled={forceCheckMutation.isPending}
            >
              {forceCheckMutation.isPending ? <Spinner /> : "Forzar verificación"}
            </Button>
          </div>
          {forceCheckMutation.isSuccess && (
            <Alert>Verificación forzada. Actualizando estado…</Alert>
          )}
          <ScraperHealthPanel />
        </TabsContent>

        {/* ── BACKUPS TAB ── */}
        <TabsContent value="backups" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Estado del backup</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Último backup:{" "}
                <strong>
                  {backupStatus?.last_backup
                    ? new Date(backupStatus.last_backup).toLocaleString("es-CL")
                    : "Sin registros"}
                </strong>
              </p>
              <p className="text-sm text-muted-foreground">
                Estado: <strong>{backupStatus?.status ?? "desconocido"}</strong>
              </p>
              <Button
                onClick={() => backupMutation.mutate()}
                disabled={backupMutation.isPending}
              >
                {backupMutation.isPending ? <Spinner /> : "Ejecutar backup ahora"}
              </Button>
              {backupMutation.isSuccess && <Alert>Backup iniciado correctamente.</Alert>}
              {backupMutation.isError && (
                <Alert variant="destructive">
                  {(backupMutation.error as Error)?.message ?? "Error al ejecutar backup."}
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── USERS TAB ── */}
        <TabsContent value="users" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Promover usuario</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="promote-username">Nombre de usuario</Label>
                <Input
                  id="promote-username"
                  value={promoteUsername}
                  onChange={(e) => setPromoteUsername(e.target.value)}
                  placeholder="username"
                />
              </div>
              <div>
                <Label htmlFor="promote-role">Rol</Label>
                <select
                  id="promote-role"
                  value={promoteRole}
                  onChange={(e) => setPromoteRole(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="admin">admin</option>
                  <option value="user">user</option>
                </select>
              </div>
              <Button
                onClick={() => promoteMutation.mutate({ username: promoteUsername, role: promoteRole })}
                disabled={promoteMutation.isPending || !promoteUsername}
              >
                {promoteMutation.isPending ? <Spinner /> : "Promover"}
              </Button>
              {promoteMutation.isSuccess && (
                <Alert>Usuario promovido correctamente.</Alert>
              )}
              {promoteMutation.isError && (
                <Alert variant="destructive">
                  {(promoteMutation.error as Error)?.message ?? "Error al promover usuario."}
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
