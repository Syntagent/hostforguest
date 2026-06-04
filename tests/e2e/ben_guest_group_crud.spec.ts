import { test, expect } from "@playwright/test";

test.describe("Host guest group CRUD", () => {
  test("create group appears in groups tab after reload", async ({ page }) => {
    await page.goto("/dashboard?tab=groups", { waitUntil: "domcontentloaded" });

    const createBtn = page.getByRole("button", { name: /create new group/i }).first();
    await expect(createBtn).toBeVisible({ timeout: 20000 });
    await createBtn.click();

    const groupName = `E2E Group ${Date.now()}`;
    await page.getByPlaceholder(/smith family|group name/i).fill(groupName);

    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const checkout = new Date(tomorrow);
    checkout.setDate(checkout.getDate() + 5);
    const fmt = (d: Date) => d.toISOString().slice(0, 10);

    await page.locator('input[type="date"]').nth(0).fill(fmt(tomorrow));
    await page.locator('input[type="date"]').nth(1).fill(fmt(checkout));

    await page.getByRole("button", { name: /^create group$/i }).click();

    await expect(page.getByText(groupName)).toBeVisible({ timeout: 15000 });

    await page.goto("/dashboard?tab=groups", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(groupName)).toBeVisible({ timeout: 20000 });
  });
});
