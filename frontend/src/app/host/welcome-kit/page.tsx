"use client";

import { WelcomeKitGenerator } from "@/components/host/WelcomeKitGenerator";
import { withAuth } from "@/contexts/auth-context";

function WelcomeKitPage() {
    return <WelcomeKitGenerator />;
}

export default withAuth(WelcomeKitPage);
