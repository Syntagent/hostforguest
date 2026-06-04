import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3055";
const apiURL = process.env.PLAYWRIGHT_API_URL || baseURL;

export default defineConfig({
  testDir: ".",
  timeout: 120000,
  workers: 1,
  testMatch: [
    "ci-guest-events.spec.ts",
    "ci-host-dashboard.spec.ts",
    "ci-onboarding-geocode.spec.ts",
  ],
  use: {
    baseURL,
    storageState: { cookies: [], origins: [] },
    // Wider than 1280px so AppLayout does not auto-collapse the sidebar (max-width: 1280px).
    viewport: { width: 1366, height: 900 },
    trace: "on-first-retry",
    extraHTTPHeaders: {},
  },
  reporter: [["list"]],
  metadata: {
    apiURL,
  },
});
