import { expect, type Page } from "@playwright/test";

export const ACCESS_CODE = process.env.E2E_GUEST_ACCESS_CODE || "";
export const GROUP_NAME = process.env.E2E_GUEST_GROUP_NAME || "E2E CI Guest Group";

export async function openGuestApp(page: Page, code: string = ACCESS_CODE) {
  if (!code) {
    throw new Error("E2E_GUEST_ACCESS_CODE is required for CI guest E2E");
  }
  await page.goto(`/guest/${code}`);
  await waitForGuestShell(page);
  const escaped = GROUP_NAME.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  await expect(page.getByRole("heading", { name: new RegExp(`Welcome.*${escaped}`, "i") })).toBeVisible({
    timeout: 60000,
  });
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
