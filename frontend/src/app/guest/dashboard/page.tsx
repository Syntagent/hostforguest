"use client";

import React from "react";
import { useRouter } from "next/navigation";

export default function GuestDashboardPage() {
  const router = useRouter();

  React.useEffect(() => {
    const code = localStorage.getItem("guest_access_code")?.trim();
    router.replace(code ? `/guest/${code}` : "/guest/join");
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-teal-600 to-green-600 px-4 text-white">
      <div className="rounded-3xl border border-white/25 bg-white/10 p-6 text-center shadow-xl backdrop-blur-md">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-white border-t-transparent" />
        <p className="text-sm text-blue-100">Opening your guest guide…</p>
      </div>
    </div>
  );
}
