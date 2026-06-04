"use client";

import React from "react";
import { useRouter } from "next/navigation";

type GuestPreferencesCodePageProps = {
  params: Promise<{ accessCode: string }> | { accessCode: string };
};

function isThenable(value: unknown): value is Promise<{ accessCode: string }> {
  return value != null && typeof (value as Promise<unknown>).then === "function";
}

/** Legacy URL: preferences editing is handled by /guest/setup/[accessCode]. */
export default function GuestPreferencesCodePage({ params }: GuestPreferencesCodePageProps) {
  const router = useRouter();

  React.useEffect(() => {
    void (async () => {
      const resolved = isThenable(params) ? await params : params;
      const code = resolved.accessCode?.trim();
      router.replace(code ? `/guest/setup/${code}` : "/guest/join");
    })();
  }, [params, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-teal-600 to-green-600 text-white">
      <p>Redirecting…</p>
    </div>
  );
}
