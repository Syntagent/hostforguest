"use client";

import React from "react";
import { AccessCodeForm } from "@/components/guest/AccessCodeForm";
import { HeroSection } from "@/components/ui/hero-section";

export default function GuestJoinPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-teal-600 to-green-600">
      <HeroSection
        title="Dobro došli u Hrvatsku! 🇭🇷"
        subtitle="Welcome to Croatia"
        description="Enter your access code to discover personalized Croatian experiences curated by your local host."
        backgroundGradient="from-blue-600 via-teal-600 to-green-600"
        showCTA={false}
      >
        <div className="mx-auto mt-12 w-full max-w-lg px-1">
          <AccessCodeForm />
        </div>
      </HeroSection>
    </div>
  );
}
