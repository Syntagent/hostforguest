/**
 * E2E: Ben host — Insights tab events feed (realtime tourism data).
 */
import { test, expect } from "@playwright/test";
import { loginAsBen, openTab } from "./ben-auth";

test.describe("Ben events insights", () => {
  test("insights tab loads events after bootstrap", async ({ page, request }) => {
    const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
    await request.post(`${apiBase}/api/v1/realtime/events/bootstrap?city=Lovran&sync_mode=regional`);

    await loginAsBen(page);
    await page.goto("/dashboard?tab=insights");
    await expect(page.getByRole("heading", { name: /Events & local happenings/i })).toBeVisible({
      timeout: 20000,
    });
    await expect(page.getByRole("button", { name: /Sync sources/i })).toBeVisible();
    await expect(page.getByText(/Source health|Upcoming|seasonal events|items for your area/i).first()).toBeVisible({
      timeout: 30000,
    });
  });

  test("overview shows tourism updates when feed has data", async ({ page, request }) => {
    const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
    await request.post(`${apiBase}/api/v1/realtime/sources/init`);

    await openTab(page, "Overview");
    await expect(page.getByText(/Croatian Tourism Updates/i)).toBeVisible({ timeout: 15000 });
  });
});
