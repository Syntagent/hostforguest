import { expect, type Page } from "@playwright/test";
import { dashboardPathForTab, HOST_TAB_LABEL_TO_ID } from "./dashboard-tab-url";

export const BEN_EMAIL = process.env.BEN_TEST_EMAIL || "benediktperak@gmail.com";
export const BEN_PASSWORD = process.env.BEN_TEST_PASSWORD || "Ben@Host1";

/** Login with retries (avoids flaky 429 / cold starts on production). */
export async function loginAsBen(page: Page) {
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      await page.goto("/login");
      await page.locator("#email").fill(BEN_EMAIL);
      await page.locator("#password").fill(BEN_PASSWORD);
      await page.getByRole("button", { name: /^Sign in$/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 30000 });
      return;
    } catch (e) {
      lastError = e;
      if (attempt < 2) await page.waitForTimeout(2500);
    }
  }
  throw lastError;
}

async function recoverDashboardSession(page: Page) {
  const overviewTab = page.getByRole("button", { name: "Overview", exact: true }).first();
  if (await overviewTab.isVisible({ timeout: 5000 }).catch(() => false)) return;

  const tryAgain = page.getByRole("button", { name: /Try Again/i });
  if (await tryAgain.isVisible({ timeout: 2000 }).catch(() => false)) {
    await tryAgain.click();
    if (await overviewTab.isVisible({ timeout: 45000 }).catch(() => false)) return;
  }

  const onLogin = await page.locator("#email").isVisible({ timeout: 2000 }).catch(() => false);
  const authRequired = await page
    .getByText("Authentication Required")
    .isVisible({ timeout: 2000 })
    .catch(() => false);
  if (onLogin || authRequired || !page.url().includes("/dashboard")) {
    await loginAsBen(page);
  }
}

export async function ensureDashboard(page: Page) {
  if (!page.url().includes("/dashboard")) {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded", timeout: 60000 });
  }

  await recoverDashboardSession(page);

  const overviewTab = page.getByRole("button", { name: "Overview", exact: true }).first();
  const loading = page.getByText("Loading your dashboard");

  if (await loading.isVisible({ timeout: 5000 }).catch(() => false)) {
    await expect(loading).toBeHidden({ timeout: 90000 });
  }

  if (!(await overviewTab.isVisible({ timeout: 5000 }).catch(() => false))) {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded", timeout: 60000 });
    await recoverDashboardSession(page);
  }

  await expect(overviewTab).toBeVisible({ timeout: 60000 });
}

export async function openTab(page: Page, label: string) {
  await ensureDashboard(page);
  const tabId = HOST_TAB_LABEL_TO_ID[label];
  if (!tabId) {
    throw new Error(`Unknown host dashboard tab label: ${label}`);
  }
  await page.goto(dashboardPathForTab(label), {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  if (tabId === "overview") {
    await expect(page).toHaveURL(/\/dashboard\/?(\?[^#]*)?$/);
    await expect(page).not.toHaveURL(/[?&]tab=/);
  } else {
    await expect(page).toHaveURL(new RegExp(`[?&]tab=${tabId}(&|$|#)`));
  }
  const tabButton = page.getByRole("button", { name: label, exact: true }).first();
  await expect(tabButton).toBeVisible({ timeout: 30000 });
}
