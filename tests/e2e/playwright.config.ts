import { defineConfig } from "@playwright/test";
import path from "path";

const authFile = path.join(__dirname, ".auth", "ben.json");
const baseURL = process.env.PLAYWRIGHT_BASE_URL || "https://hostforguest.syntagent.com";

export default defineConfig({
  testDir: ".",
  timeout: 120000,
  workers: 1,
  globalSetup: require.resolve("./global-setup"),
  projects: [
    {
      name: "host",
      testMatch: [
        "ben_host_dashboard.spec.ts",
        "ben_host_components.spec.ts",
        "ben_guest_host_view.spec.ts",
        "ben_events_insights.spec.ts",
        "ben_guest_group_crud.spec.ts",
      ],
      use: {
        baseURL,
        storageState: authFile,
        viewport: { width: 1440, height: 900 },
        trace: "on-first-retry",
      },
    },
    {
      name: "guest",
      testMatch: [
        "ben_guest_interaction.spec.ts",
        "ben_guest_all_components.spec.ts",
        "ben_guest_setup_wizard.spec.ts",
        "ben_guest_events.spec.ts",
      ],
      use: {
        baseURL,
        storageState: { cookies: [], origins: [] },
        viewport: { width: 1440, height: 900 },
        trace: "on-first-retry",
      },
    },
  ],
  reporter: [["list"]],
});
