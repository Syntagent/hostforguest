"use client";

import { HostDashboard } from "@/components/dashboard/host-dashboard";
import { withAuth } from "@/contexts/auth-context";

function DashboardPage() {
  return <HostDashboard />;
}

export default withAuth(DashboardPage);
