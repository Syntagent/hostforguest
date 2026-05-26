import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const DEV_EMAIL =
  process.env.DEV_LOGIN_SEED_EMAIL || "dev@touristguide.local";
export const DEV_PASSWORD =
  process.env.DEV_LOGIN_SEED_PASSWORD || "devlogin123";

const API_BASE = process.env.PLAYWRIGHT_API_URL || "http://127.0.0.1:8000";

async function fetchDevSessionToken(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${API_BASE}/api/v1/hosts/login`, {
    data: { email: DEV_EMAIL, password: DEV_PASSWORD },
  });
  expect(res.ok()).toBeTruthy();
  const body = (await res.json()) as { session_token?: string };
  if (!body.session_token) {
    throw new Error("Dev login response missing session_token");
  }
  return body.session_token;
}

async function isHostShellVisible(page: Page): Promise<boolean> {
  return page
    .getByRole("button", { name: "Guests", exact: true })
    .first()
    .isVisible({ timeout: 5000 })
    .catch(() => false);
}

/** Sign in via API, reload so AuthProvider picks up the session, then open dashboard. */
export async function loginAsDevHost(page: Page, request: APIRequestContext) {
  const token = await fetchDevSessionToken(request);
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.evaluate((sessionToken) => {
    localStorage.setItem("session_token", sessionToken);
  }, token);
  // AuthProvider only checks localStorage on mount — reload after seeding token.
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await waitForDashboardShell(page);
  await expect(page.getByRole("button", { name: "Guests", exact: true }).first()).toBeVisible({
    timeout: 60000,
  });
}

async function waitForDashboardShell(page: Page) {
  const loading = page.getByText(/Checking authentication|Loading your dashboard/i);
  if (await loading.isVisible({ timeout: 5000 }).catch(() => false)) {
    await expect(loading).toBeHidden({ timeout: 90000 });
  }
}

export async function ensureHostDashboard(page: Page, request: APIRequestContext) {
  const overviewTab = page.getByRole("button", { name: "Overview", exact: true }).first();

  if (!page.url().includes("/dashboard")) {
    await loginAsDevHost(page, request);
  } else if (!(await isHostShellVisible(page))) {
    const onLogin = await page.locator("#email").isVisible({ timeout: 2000 }).catch(() => false);
    if (onLogin) {
      await loginAsDevHost(page, request);
    } else {
      await page.goto("/dashboard", { waitUntil: "domcontentloaded", timeout: 60000 });
      await waitForDashboardShell(page);
    }
  }

  await waitForDashboardShell(page);

  if (!(await isHostShellVisible(page))) {
    await loginAsDevHost(page, request);
  }

  await expect(overviewTab).toBeVisible({ timeout: 60000 });
}

export async function openHostTab(page: Page, label: string) {
  let tab = page.getByRole("button", { name: label, exact: true }).first();
  if (!(await tab.isVisible({ timeout: 3000 }).catch(() => false))) {
    throw new Error(`Host tab "${label}" not visible on dashboard`);
  }
  await tab.scrollIntoViewIfNeeded();
  await tab.click({ timeout: 30000 });
  await page.waitForTimeout(300);
}
