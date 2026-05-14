"use client";

import React, { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function PreferencesRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get("accessCode");

  useEffect(() => {
    if (code) {
      router.replace(`/guest/setup/${code}`);
    } else {
      router.replace("/guest/join");
    }
  }, [code, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-teal-600 to-green-600 text-white">
      <p>Redirecting…</p>
    </div>
  );
}

/** Legacy URL: use /guest/setup/[accessCode] for the full wizard. */
export default function GuestPreferencesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-teal-600 to-green-600 text-white">
          Loading…
        </div>
      }
    >
      <PreferencesRedirect />
    </Suspense>
  );
}
