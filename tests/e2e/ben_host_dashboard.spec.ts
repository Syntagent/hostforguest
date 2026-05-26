/**
 * E2E: Ben Test host — login, dashboard tabs, create attraction & guest group.
 */
import { test, expect } from "@playwright/test";
import { BEN_EMAIL, loginAsBen, openTab } from "./ben-auth";

test.describe.configure({ mode: "serial" });

test.describe("Ben Test host dashboard", () => {
  test("login and overview", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(
      page.getByText(/Ben Test|Dobro|Welcome|Overview|dashboard/i).first()
    ).toBeVisible({ timeout: 30000 });
  });

  test("create attraction", async ({ page }) => {
    await openTab(page, "Attractions");
    await page.getByRole("button", { name: /Add New Attraction/i }).click();

    const name = `Ben E2E ${Date.now()}`;
    await page.getByPlaceholder(/attraction|name/i).first().fill(name);
    const textareas = page.locator("textarea");
    await textareas.first().fill("E2E test attraction description for Ben Test host in Lovran.");
    await page.locator('input[placeholder*="City"], input[placeholder*="city"]').first().fill("Lovran");
    await page.locator('input[placeholder*="Address"], input[placeholder*="address"]').first().fill("Lovran, Croatia");

    await page.getByRole("button", { name: /Create Attraction/i }).click();
    await expect(page.getByText(name)).toBeVisible({ timeout: 30000 });
  });

  test("create guest group", async ({ page }) => {
    await page.goto("/dashboard");
    await openTab(page, "Guests");
    await page.getByRole("button", { name: "Create New Group" }).click();
    await expect(
      page.getByRole("heading", { name: "Create New Guest Group" })
    ).toBeVisible();
    const gname = `Ben Group ${Date.now()}`;
    await page
      .getByPlaceholder("e.g., Smith Family, Business Trip Group")
      .fill(gname);
    const createBtn = page.getByRole("button", { name: "Create Group", exact: true });
    await expect(createBtn).toBeEnabled();
    await createBtn.click();
    await expect(page.getByRole("heading", { name: "Create New Guest Group" })).toBeHidden({
      timeout: 30000,
    });
    await expect(page.getByText(gname)).toBeVisible({ timeout: 30000 });
  });

  test("account tab", async ({ page }) => {
    await page.goto("/dashboard");
    await openTab(page, "Account");
    await expect(page.getByText(BEN_EMAIL, { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
  });

  test("channels and maintenance tabs load", async ({ page }) => {
    await page.goto("/dashboard");
    await openTab(page, "Channels");
    await expect(page.getByText(/Booking|channel/i).first()).toBeVisible({ timeout: 15000 });
    await openTab(page, "Maintenance");
    await expect(page.getByText(/issue|maintenance|schedule/i).first()).toBeVisible({ timeout: 15000 });
  });

  test("remaining dashboard tabs load", async ({ page }) => {
    await page.goto("/dashboard");
    const tabs: { label: string; pattern: RegExp }[] = [
      { label: "Overview", pattern: /overview|welcome|Ben Test|Dobro/i },
      { label: "Stay", pattern: /accommodation|property|address/i },
      { label: "Routes", pattern: /route|itinerary|template/i },
      { label: "Adaptation", pattern: /adaptation|project/i },
      { label: "Map", pattern: /map|attraction/i },
      { label: "Discover", pattern: /discover|search|scrape/i },
      { label: "Cleaning", pattern: /cleaning|checkout|provider/i },
      { label: "Insights", pattern: /insight|recommendation|analytics/i },
    ];
    for (const { label, pattern } of tabs) {
      await openTab(page, label);
      await expect(page.getByText(pattern).first()).toBeVisible({ timeout: 20000 });
    }
  });
});
