"use client";

import React from "react";
import { GuestProvider } from "@/contexts/guest-context";
import { GuestDashboard } from "@/components/guest/GuestDashboard";

export default function GuestDashboardPage() {
  return (
    <GuestProvider>
      <div className="min-h-screen bg-gradient-to-br from-blue-600 via-teal-600 to-green-600">
        <GuestDashboard />
      </div>
    </GuestProvider>
  );
}
