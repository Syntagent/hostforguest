import { Suspense } from "react";
import { GuestOnboardingWizard } from "@/components/guest/GuestOnboardingWizard";

interface GuestSetupPageProps {
  params: Promise<{ accessCode: string }>;
}

function SetupFallback() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-gradient-to-br from-blue-600 via-teal-600 to-green-600 text-white">
      <div
        className="h-9 w-9 animate-spin rounded-full border-2 border-white border-t-transparent"
        aria-hidden
      />
      <p className="text-sm text-blue-100">Loading setup…</p>
    </div>
  );
}

export default async function GuestSetupPage({ params }: GuestSetupPageProps) {
  const { accessCode } = await params;

  return (
    <div className="min-h-screen overflow-x-hidden bg-gradient-to-br from-blue-600 via-teal-600 to-green-600">
      <Suspense fallback={<SetupFallback />}>
        <GuestOnboardingWizard accessCode={accessCode} />
      </Suspense>
    </div>
  );
}
