import { Suspense } from "react";
import { ErrorBoundary } from "@/components/error-boundary";
import { Skeleton } from "@/components/ui/skeleton";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function AsyncBoundary({ children, fallback }: Props) {
  return (
    <ErrorBoundary fallback={fallback}>
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}
