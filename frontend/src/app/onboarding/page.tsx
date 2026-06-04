"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { HostOnboarding } from "@/components/onboarding/host-onboarding";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useAuth } from "@/contexts/auth-context";

function OnboardingPageContent() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const searchParams = useSearchParams();
  const fromLogin = searchParams.get("from") === "login";
  const forceRegistration = searchParams.get("register") === "1";

  const handleOnboardingComplete = async (_hostData?: Record<string, unknown>) => {
    void _hostData;
    await refreshUser();
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen">
      {fromLogin && (
        <div className="mx-auto max-w-4xl px-4 pt-6">
          <Alert className="border-amber-200 bg-amber-50 text-amber-950">
            <AlertTitle>Complete your host profile</AlertTitle>
            <AlertDescription>
              You signed in, but your property profile is not set up yet. Finish the steps below,
              then you can use the dashboard. Already done?{" "}
              <Link href="/dashboard" className="font-medium underline">
                Open dashboard
              </Link>
            </AlertDescription>
          </Alert>
        </div>
      )}
      <HostOnboarding
        onComplete={handleOnboardingComplete}
        forceRegistration={forceRegistration}
      />
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-muted/30" />}>
      <OnboardingPageContent />
    </Suspense>
  );
}
