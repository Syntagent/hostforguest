"use client";

import { HostOnboarding } from "@/components/onboarding/host-onboarding";

export default function OnboardingPage() {
  const handleOnboardingComplete = (hostData: Record<string, unknown>) => {
    console.log('🎉 Onboarding completed successfully!');
    console.log('Final host data:', hostData);
    
    // Show success message before redirect
    alert('🎉 Congratulations! Your host profile has been created successfully. Please login to access your dashboard.');
    
    // Small delay to let user see the success message
    setTimeout(() => {
      console.log('🔄 Redirecting to login...');
      window.location.href = '/login';
    }, 2000);
  };

  return (
    <HostOnboarding 
      onComplete={handleOnboardingComplete}
    />
  );
}
