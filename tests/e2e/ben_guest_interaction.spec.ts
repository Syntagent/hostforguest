/**
 * E2E: Guest-side interaction (no host session).
 */
import { test, expect } from "@playwright/test";

const ACCESS_CODE = process.env.BEN_GUEST_ACCESS_CODE || "72HQ5TJL";

test.describe("Ben scenario guest interaction", () => {
  test("join with access code opens guest app", async ({ page }) => {
    await page.goto("/guest/join");
    await page.locator("#accessCode").fill(ACCESS_CODE);
    await page.getByRole("button", { name: /Continue/i }).click();
    await expect(page).toHaveURL(new RegExp(`/guest/${ACCESS_CODE}`), { timeout: 30000 });
    await expect(
      page.getByRole("heading", { name: /Welcome.*Ben Scenario Family/i })
    ).toBeVisible({ timeout: 45000 });
  });

  test("guest dashboard shows recommendations", async ({ page }) => {
    await page.goto(`/guest/${ACCESS_CODE}`);
    await expect(
      page.getByRole("heading", { name: /Welcome, Ben Scenario Family/i })
    ).toBeVisible({ timeout: 45000 });
  });
});
