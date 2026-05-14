"use client";

import dynamic from "next/dynamic";
import React from "react";

/**
 * Load the full guest dashboard only on the client. Prevents SSR from evaluating
 * the heavy dependency graph (e.g. Leaflet / react-leaflet) which can cause 500s
 * on the document request in some Next + Windows setups.
 */
const GuestInterface = dynamic(
  () => import("./guest-interface").then((mod) => ({ default: mod.GuestInterface })),
  {
    ssr: false,
    loading: () => (
      <div className="min-h-screen bg-background px-4 py-8 md:px-6 lg:px-8">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <div className="skeleton h-24 rounded-3xl md:h-28" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="skeleton h-48 rounded-3xl md:h-56" />
            <div className="skeleton h-48 rounded-3xl md:h-56" />
            <div className="skeleton h-48 rounded-3xl md:h-56" />
          </div>
          <p className="text-center text-sm text-muted-foreground">
            Loading your guide… this only takes a moment.
          </p>
        </div>
      </div>
    ),
  }
);

interface GuestInterfaceClientProps {
  accessCode: string;
}

export const GuestInterfaceClient: React.FC<GuestInterfaceClientProps> = ({
  accessCode,
}) => {
  return <GuestInterface accessCode={accessCode} />;
};
