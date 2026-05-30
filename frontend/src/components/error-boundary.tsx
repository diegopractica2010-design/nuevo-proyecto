"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error("[ErrorBoundary]", error, info);
    if (typeof window !== "undefined" && (window as Window & { __sentry?: { captureException: (e: Error) => void } }).__sentry) {
      (window as Window & { __sentry?: { captureException: (e: Error) => void } }).__sentry?.captureException(error);
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <Card className="m-4">
          <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
            <AlertTriangle className="h-8 w-8 text-destructive" />
            <p className="text-sm text-muted-foreground">
              {this.state.error?.message ?? "Algo salió mal."}
            </p>
            <Button size="sm" onClick={() => this.setState({ hasError: false, error: null })}>
              Intentar de nuevo
            </Button>
          </CardContent>
        </Card>
      );
    }
    return this.props.children;
  }
}
