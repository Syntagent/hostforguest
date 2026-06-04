"use client";

import { Suspense } from "react";
import { HostDashboard } from "@/components/dashboard/host-dashboard";
import { withAuth } from "@/contexts/auth-context";

function DashboardLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 via-teal-600 to-green-600">
      <p className="text-white text-sm">Loading dashboard…</p>
    </div>
  );
}

function DashboardPage() {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <HostDashboard />
    </Suspense>
  );
}

export default withAuth(DashboardPage);
