import dynamic from "next/dynamic";

export const dynamic = "force-dynamic";

const DashboardClient = dynamic(() => import("./dashboard-client"), {
  ssr: false,
  loading: () => (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-teal-600 to-green-600">
      <p className="text-sm text-white">Loading dashboard...</p>
    </div>
  ),
});

export default function DashboardPage() {
  return <DashboardClient />;
}
