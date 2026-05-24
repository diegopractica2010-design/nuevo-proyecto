import { AppShell } from "@/components/layout/app-shell";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
