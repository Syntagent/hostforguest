/**
 * Login form must show API errors (regression: clearError effect wiped messages).
 */
import { test, expect } from "@playwright/test";

const DEV_EMAIL = "dev@touristguide.local";

test.describe("Login feedback", () => {
  test("failed sign-in shows visible error for dev credentials", async ({ page }) => {
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Host sign in/i })).toBeVisible();

    await page.locator("#email").fill(DEV_EMAIL);
    await page.locator("#password").fill("wrong-password-on-purpose");
    await page.getByRole("button", { name: /^Sign in$/i }).click();

    const alert = page.locator("form").getByRole("alert");
    await expect(alert).toBeVisible({ timeout: 15000 });
    await expect(alert).toContainText(/invalid email or password/i);

    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("button", { name: /^Sign in$/i })).toBeEnabled();
  });
});
