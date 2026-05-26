import dynamic from "next/dynamic";
import { AppLayout } from "@/layouts/app-layout";
import { SearchDashboard } from "@/features/search/components/search-dashboard";

const ShoppingListWorkbench = dynamic(
  () =>
    import("@/features/shopping-list/components/shopping-list-workbench").then(
      (m) => m.ShoppingListWorkbench
    ),
  { loading: () => <div className="h-64 animate-pulse rounded-xl bg-muted" /> }
);

export default function Home() {
  return (
    <AppLayout>
      <div className="space-y-12">
        <SearchDashboard />
        <ShoppingListWorkbench />
      </div>
    </AppLayout>
  );
}
