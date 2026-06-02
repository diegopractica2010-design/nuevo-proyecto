import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductDetailClient } from "./product-detail-client";

export default function ProductDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <ProductDetailClient />
    </Suspense>
  );
}
