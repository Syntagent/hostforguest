import { expect, type Page } from "@playwright/test";

export async function waitForGuestShell(page: Page) {
  const loading = page.getByText("Loading your guide");
  if (await loading.isVisible({ timeout: 3000 }).catch(() => false)) {
    await expect(loading).toBeHidden({ timeout: 90000 });
  }
}

export async function expectGuestWelcome(page: Page, groupName?: string) {
  const shell = page.getByTestId("app-nav-welcome").or(
    page.getByRole("heading", { name: /Welcome/i }).first()
  );
  await expect(shell.first()).toBeVisible({ timeout: 90000 });
  if (groupName?.trim()) {
    const escaped = groupName.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    await expect(page.getByRole("heading", { name: new RegExp(escaped, "i") }).first()).toBeVisible({
      timeout: 15000,
    }).catch(() => undefined);
  }
}
