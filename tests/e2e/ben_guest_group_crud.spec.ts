import { test, expect } from "@playwright/test";

test.describe("Host guest group CRUD", () => {
  test("create group appears in groups tab after reload", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /dashboard|host/i }).first().click({ timeout: 15000 }).catch(() => {});
    await page.goto("/host/dashboard", { waitUntil: "domcontentloaded" });

    const groupsTab = page.getByRole("button", { name: /^groups$/i }).or(
      page.getByRole("tab", { name: /^groups$/i })
    );
    if (await groupsTab.count()) {
      await groupsTab.first().click();
    }

    const createBtn = page.getByRole("button", { name: /create.*group|new group/i }).first();
    await expect(createBtn).toBeVisible({ timeout: 20000 });
    await createBtn.click();

    const groupName = `E2E Group ${Date.now()}`;
    await page.getByPlaceholder(/smith family|group name/i).fill(groupName);
    await page.getByRole("button", { name: /^create group$/i }).click();

    await expect(page.getByText(groupName)).toBeVisible({ timeout: 15000 });

    await page.reload({ waitUntil: "domcontentloaded" });
    if (await groupsTab.count()) {
      await groupsTab.first().click();
    }
    await expect(page.getByText(groupName)).toBeVisible({ timeout: 20000 });
  });
});
