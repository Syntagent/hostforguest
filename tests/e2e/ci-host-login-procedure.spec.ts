/**
 * End-to-end: login page procedure copy + dev sign-in → onboarding when profile incomplete.
 */
import { test, expect } from "@playwright/test";

test.describe("Host login procedure", () => {
  test("login page shows how host access works", async ({ page }) => {
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("How host access works")).toBeVisible();
    await expect(page.getByText(/First time here/i)).toBeVisible();
    await expect(page.getByText(/Sign in only works after onboarding/i)).toBeVisible();
  });

  test("dev sign-in redirects to onboarding when profile is placeholder", async ({ page }) => {
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Dev login" }).click();
    await page.waitForURL(/\/onboarding/, { timeout: 30000 });
    await expect(page).toHaveURL(/\/onboarding/);
    await expect(page.getByText(/Complete your host profile/i)).toBeVisible();
  });
});
