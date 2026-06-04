/**
 * Full onboarding: register a new host and complete every step (no skips).
 */
import { test, expect } from "@playwright/test";

const STORY =
  "Our family villa in Lovran overlooks Kvarner bay. I guide guests to konobas, forest trails, and quiet coves away from summer crowds.";

test("register and complete full onboarding without skipping steps", async ({ page }) => {
  const email = `e2e.full.${Date.now()}@touristguide.local`;
  const password = "TestHost123!";

  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  await page.goto("/onboarding?register=1");
  await expect(page.getByRole("heading", { name: /Create Your Account/i })).toBeVisible({
    timeout: 20000,
  });
  await page.locator("#full_name").fill("E2E Full Host");
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
  await expect(page.locator(".text-red-700")).toHaveCount(0);

  await page.locator('input[name="business_name"]').fill("Villa E2E Full Lovran");
  const formSelects = page.locator("form select");
  await formSelects.nth(0).selectOption("villa");
  await page.locator('input[name="city"]').fill("Lovran");
  await formSelects.nth(1).selectOption("Kvarner");
  await formSelects.nth(2).selectOption("born_here");

  const guestTypes = [
    "Young couples",
    "Families with children",
    "Solo travelers",
    "Groups of friends",
    "Business travelers",
    "Senior travelers",
    "Adventure seekers",
    "Cultural enthusiasts",
  ];
  for (const guest of guestTypes) {
    await page.locator("label").filter({ hasText: guest }).click();
  }

  await page.locator('textarea[name="location_story"]').fill(STORY);

  for (const lang of ["German", "Italian", "French", "Spanish"]) {
    await page.locator("label").filter({ hasText: lang }).click();
  }
  for (const specialty of [
    "Local History",
    "Gastronomy",
    "Nature Activities",
    "Cultural Events",
    "Wine Tourism",
    "Adventure Sports",
  ]) {
    await page.locator("label").filter({ hasText: specialty }).click();
  }

  await page
    .getByPlaceholder("e.g., Oprić 71, 51450 Lovran, Croatia")
    .fill("Oprić 71, 51450 Lovran, Croatia");
  await page.waitForResponse((r) => r.url().includes("/geocode") && r.ok(), { timeout: 15000 })
    .catch(() => undefined);
  await expect(page.getByText(/Locating address/i)).toBeHidden({ timeout: 10000 });
  await expect(page.getByText(/Location verified/i).first()).toBeVisible({ timeout: 15000 });

  await page.getByRole("button", { name: /Continue to AI Profile/i }).click();

  await expect(page.getByText(/Your Selections Summary/i)).toBeVisible({ timeout: 120000 });

  const pickSecondOption = async (title: string) => {
    const column = page.locator("div.bg-white.rounded-xl").filter({
      has: page.getByRole("heading", { name: title }),
    });
    const options = column.locator("div.cursor-pointer");
    if ((await options.count()) > 1) {
      await options.nth(1).click();
    }
  };
  await pickSecondOption("Business Description");
  await pickSecondOption("Welcome Messages");
  await pickSecondOption("Host Story");

  await page.getByRole("button", { name: /Continue with Selections/i }).click();

  const discoverBtn = page.getByRole("button", { name: /Discover Attractions/i });
  if (await discoverBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
    await discoverBtn.click();
  }

  const continueReview = page.getByRole("button", { name: /Continue to Review/i });
  await expect(continueReview).toBeVisible({ timeout: 180000 });
  const reviewLabel = await continueReview.textContent();
  expect(reviewLabel).toMatch(/[1-9]\d* attractions/);

  await page.getByRole("button", { name: /Add Your Own Hidden Gem/i }).click();
  await expect(page.getByRole("heading", { name: "Add Custom Attraction" })).toBeVisible();
  const modal = page.locator(".fixed.inset-0");
  await modal.getByPlaceholder(/Hidden Beach at Preluk/i).fill("E2E Secret Cove Lovran");
  await modal
    .getByPlaceholder(/Share your local knowledge about this place/i)
    .fill("Small pebble cove below the coastal path — best at sunrise, bring water shoes.");
  await modal.locator("select").first().selectOption("nature");
  await modal.getByRole("button", { name: /^Add Attraction$/i }).click();

  await expect(continueReview).toBeVisible({ timeout: 15000 });
  await continueReview.click();

  await expect(page.getByRole("button", { name: /Launch My Host Profile/i })).toBeVisible({
    timeout: 30000,
  });
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/complete-onboarding") && r.ok(),
      { timeout: 120000 }
    ),
    page.getByRole("button", { name: /Launch My Host Profile/i }).click(),
  ]);

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 60000 });
  await expect(page.getByText(/Property profile incomplete/i)).not.toBeVisible({
    timeout: 15000,
  });
  await expect(page.getByText(/Villa E2E Full Lovran/i).first()).toBeVisible();
  await expect(page.getByText(/Lovran/i).first()).toBeVisible();
});
