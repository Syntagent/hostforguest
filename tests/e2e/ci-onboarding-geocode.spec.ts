/**
 * CI onboarding geocode smoke — property step must resolve GPS before continue.
 */
import { test, expect } from "@playwright/test";

const STORY =
  "Our family villa in Lovran overlooks Kvarner bay. I guide guests to konobas, forest trails, and quiet coves away from summer crowds.";

test("onboarding property step geocodes address before continue", async ({ page }) => {
  const email = `e2e.geo.${Date.now()}@touristguide.local`;
  const password = "TestHost123!";

  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  await page.goto("/onboarding?register=1");
  await expect(page.getByRole("heading", { name: /Create Your Account/i })).toBeVisible({
    timeout: 20000,
  });

  await page.locator("#full_name").fill("E2E Geocode Host");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.locator("#confirmPassword").fill(password);

  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/hosts/register") && r.status() === 201),
    page.waitForResponse((r) => r.url().includes("/hosts/login") && r.ok()),
    page.getByRole("button", { name: /Create Account & Continue/i }).click(),
  ]);

  await expect(page.getByRole("heading", { name: /Basic Information/i })).toBeVisible({
    timeout: 30000,
  });

  await page.locator('input[name="business_name"]').fill("Geocode E2E Villa");
  const formSelects = page.locator("form select");
  await formSelects.nth(0).selectOption("villa");
  await page.locator('input[name="city"]').fill("Lovran");
  await formSelects.nth(1).selectOption("Kvarner");
  await formSelects.nth(2).selectOption("born_here");
  await page.locator("label").filter({ hasText: "Young couples" }).click();
  await page.locator('textarea[name="location_story"]').fill(STORY);

  await page
    .getByPlaceholder("e.g., Oprić 71, 51450 Lovran, Croatia")
    .fill("Oprić 71, 51450 Lovran, Croatia");

  await page.waitForResponse((r) => r.url().includes("/geocode") && r.ok(), { timeout: 20000 });
  await expect(page.getByText(/Locating address/i)).toBeHidden({ timeout: 15000 });
  await expect(page.getByText(/Location verified/i).first()).toBeVisible({ timeout: 15000 });

  await page.getByRole("button", { name: /Continue to AI Profile/i }).click();
  await expect(page.getByText(/Your Selections Summary|AI Profile/i).first()).toBeVisible({
    timeout: 60000,
  });
});
