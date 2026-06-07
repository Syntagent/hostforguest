import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3055";

export default defineConfig({
  testDir: ".",
  workers: 1,
  testMatch: [
    "ci-login-feedback.spec.ts",
    "ci-host-login-procedure.spec.ts",
    "ci-host-dashboard.spec.ts",
    "ci-guest-events.spec.ts",
    "ci-onboarding-geocode.spec.ts",
    "complete-full-onboarding.spec.ts",
  ],
  timeout: 300000,
  use: {
    baseURL,
    viewport: { width: 1280, height: 900 },
    trace: "on-first-retry",
  },
  reporter: [["list"]],
});
