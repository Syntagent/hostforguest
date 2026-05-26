/**
 * Host-side checks for Ben scenario guest group (uses saved auth).
 */
import { test, expect } from "@playwright/test";
import { openTab } from "./ben-auth";

const ACCESS_CODE = process.env.BEN_GUEST_ACCESS_CODE || "72HQ5TJL";
const SCENARIO = "Ben Scenario Family 2026";

async function openScenarioGroupDetails(page: import("@playwright/test").Page) {
  const card = page
    .locator("div.rounded-xl")
    .filter({ has: page.getByRole("heading", { name: SCENARIO, exact: true }) });
  await expect(card).toBeVisible({ timeout: 20000 });
  await card.getByRole("button", { name: "View Details" }).click();
  const modal = page.getByTestId("group-details-modal");
  await expect(modal).toBeVisible({ timeout: 15000 });
  await expect(modal.getByRole("heading", { name: SCENARIO, exact: true })).toBeVisible();
  return modal;
}

test.describe("Ben scenario — host view", () => {
  test("host sees scenario group with registered guests", async ({ page }) => {
    await openTab(page, "Guests");
    await expect(page.getByRole("heading", { name: SCENARIO, exact: true })).toBeVisible({
      timeout: 20000,
    });
    const modal = await openScenarioGroupDetails(page);
    await expect(modal.getByText("Ana Perak", { exact: true })).toBeVisible({ timeout: 20000 });
    await expect(modal.getByText("Marko Perak", { exact: true })).toBeVisible();
    await expect(modal.getByText("Luka Perak", { exact: true })).toBeVisible();
  });

  test("host sees guest-saved event ideas in group details", async ({ page, request }) => {
    const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
    const event = {
      id: `e2e-host-plan-${Date.now()}`,
      title: `E2E saved event ${Date.now()}`,
      source: "e2e",
    };

    const saveRes = await request.post(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events`,
      {
        data: {
          event_id: event.id,
          title: event.title,
          source: event.source,
        },
      }
    );
    expect(saveRes.ok()).toBeTruthy();

    await openTab(page, "Guests");
    const modal = await openScenarioGroupDetails(page);
    await expect(modal.getByRole("heading", { name: "Saved Event Ideas" })).toBeVisible({
      timeout: 20000,
    });
    await expect(modal.getByText(event.title, { exact: true })).toBeVisible();
    const row = modal.locator('[data-testid="saved-event-ideas"] > div').filter({
      hasText: event.title,
    });
    await row.getByRole("button", { name: "Mark planned" }).click();
    await expect(row.getByText("Planned", { exact: true })).toBeVisible({ timeout: 15000 });
  });

  test("fourth guest via API appears in group details", async ({ page, request }) => {
    const guestName = `Ivana Test${Date.now()}`;
    const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
    const prefRes = await request.post(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/preferences`,
      {
        data: {
          guest_name: guestName,
          age_category: "adult",
          personal_interests: ["nature", "food"],
          dietary_needs: [],
          cultural_interests: ["history"],
          food_interests: ["food"],
          language_preference: "en",
          mobility_notes: "Mobility: high\nBudget: medium",
        },
      }
    );
    expect(prefRes.ok()).toBeTruthy();

    await openTab(page, "Guests");
    const modal = await openScenarioGroupDetails(page);
    await expect(modal.getByText(guestName, { exact: true })).toBeVisible({ timeout: 20000 });
  });
});
