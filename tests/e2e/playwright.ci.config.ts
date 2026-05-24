import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3055";
const apiURL = process.env.PLAYWRIGHT_API_URL || "http://127.0.0.1:8000";

export default defineConfig({
  testDir: ".",
  timeout: 120000,
  workers: 1,
  testMatch: ["ci-guest-events.spec.ts", "ci-host-dashboard.spec.ts"],
  use: {
    baseURL,
    storageState: { cookies: [], origins: [] },
    viewport: { width: 1280, height: 900 },
    trace: "on-first-retry",
    extraHTTPHeaders: {},
  },
  reporter: [["list"]],
  metadata: {
    apiURL,
  },
});
