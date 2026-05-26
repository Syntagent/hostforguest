import { expect, type Page } from "@playwright/test";

export const ACCESS_CODE = process.env.BEN_GUEST_ACCESS_CODE || "72HQ5TJL";
export const SCENARIO_GROUP = "Ben Scenario Family 2026";

export async function openGuestApp(page: Page, code: string = ACCESS_CODE) {
  await page.goto(`/guest/${code}`);
  await expect(
    page.getByRole("heading", { name: new RegExp(`Welcome.*${SCENARIO_GROUP.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`, "i") })
  ).toBeVisible({ timeout: 60000 });
}

export async function openGuestTab(page: Page, label: string) {
  const tab = page.getByRole("button", { name: label, exact: true }).first();
  await tab.scrollIntoViewIfNeeded();
  await tab.click({ timeout: 30000 });
  await page.waitForTimeout(400);
}

export async function waitForGuestShell(page: Page) {
  const loading = page.getByText("Loading your guide");
  if (await loading.isVisible({ timeout: 3000 }).catch(() => false)) {
    await expect(loading).toBeHidden({ timeout: 90000 });
  }
}
