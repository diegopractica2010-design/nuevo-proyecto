import dynamic from "next/dynamic";
import { AppLayout } from "@/layouts/app-layout";
import { SearchDashboard } from "@/features/search/components/search-dashboard";
import { ScraperHealthPanel } from "@/features/health/components/scraper-health-panel";

const ShoppingListWorkbench = dynamic(
  () => import("@/features/shopping-list/components/shopping-list-workbench").then((module) => module.ShoppingListWorkbench),
  {
    loading: () => <div className="h-96 rounded-lg border border-white/10 bg-white/[0.04]" />
  }
);

export default function Home() {
  return (
    <AppLayout>
      <div className="space-y-8">
        <SearchDashboard />
        <ShoppingListWorkbench />
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
          <section className="rounded-lg border border-white/10 bg-white/[0.04] p-6">
            <p className="text-sm font-semibold text-primary">Architecture</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-normal">Frontend SaaS, backend-compatible.</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
              Feature modules isolate search, comparison and health. React Query owns server state,
              Zustand owns interface preferences, and typed services preserve the existing FastAPI contracts.
            </p>
          </section>
          <ScraperHealthPanel />
        </div>
      </div>
    </AppLayout>
  );
}
