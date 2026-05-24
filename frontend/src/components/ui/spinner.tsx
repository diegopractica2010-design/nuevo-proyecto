"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Loader } from "lucide-react";

const Spinner = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { size?: "sm" | "md" | "lg" }
>(({ className, size = "md", ...props }, ref) => {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8"
  };

  return (
    <div ref={ref} className={cn("flex items-center justify-center", className)} {...props}>
      <Loader className={cn("animate-spin", sizeClasses[size])} />
    </div>
  );
});
Spinner.displayName = "Spinner";

export { Spinner };
