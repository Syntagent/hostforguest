"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface GuestRegisterPageProps {
  params: Promise<{ accessCode: string }>;
}

/** Legacy URL: registration is handled by /guest/setup/[accessCode]. */
export default function GuestRegisterPage({ params }: GuestRegisterPageProps) {
  const router = useRouter();
  const [accessCode, setAccessCode] = useState<string>("");

  useEffect(() => {
    void params.then(({ accessCode: code }) => {
      setAccessCode(code);
      router.replace(`/guest/setup/${code}`);
    });
  }, [params, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-teal-600 to-green-600 text-white">
      <p>{accessCode ? "Opening setup…" : "Loading…"}</p>
    </div>
  );
}
