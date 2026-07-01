"use client";

import { usePathname } from "next/navigation";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export function RouteErrorBoundary({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return <ErrorBoundary key={pathname}>{children}</ErrorBoundary>;
}

