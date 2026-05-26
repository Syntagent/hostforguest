"use client";

import { useRouter } from "next/navigation";
import { HostOnboarding } from "@/components/onboarding/host-onboarding";

export default function OnboardingPage() {
  const router = useRouter();

  const handleOnboardingComplete = (_hostData?: Record<string, unknown>) => {
    void _hostData;
    router.push("/dashboard");
  };

  return <HostOnboarding onComplete={handleOnboardingComplete} />;
}
