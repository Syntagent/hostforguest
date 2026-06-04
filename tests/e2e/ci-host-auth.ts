import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { dashboardPathForTab, HOST_TAB_LABEL_TO_ID } from "./dashboard-tab-url";

export const DEV_EMAIL =
  process.env.DEV_LOGIN_SEED_EMAIL || "dev@touristguide.local";
export const DEV_PASSWORD =
  process.env.DEV_LOGIN_SEED_PASSWORD || "devlogin123";

const API_BASE = process.env.PLAYWRIGHT_API_URL || "http://127.0.0.1:8000";

/** Serial CI specs reuse one page — avoid redundant API re-logins that can race AuthProvider. */
let hostSessionReady = false;

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

async function waitForHostShell(page: Page, attempts = 60) {
  await waitForDashboardShell(page);
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await isHostShellVisible(page)) {
      hostSessionReady = true;
      return;
    }
    await page.waitForTimeout(1000);
  }
}

async function loginViaUiForm(page: Page) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.locator("#email").fill(DEV_EMAIL);
  await page.locator("#password").fill(DEV_PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await waitForHostShell(page);
}

/** Sign in via API token seed (fast) with UI form fallback when AuthProvider races. */
export async function loginAsDevHost(page: Page, request: APIRequestContext) {
  hostSessionReady = false;

  try {
    const token = await fetchDevSessionToken(request);
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await page.evaluate((sessionToken) => {
      localStorage.setItem("session_token", sessionToken);
    }, token);
    // AuthProvider only checks localStorage on mount — reload after seeding token.
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await waitForHostShell(page, 20);
    if (hostSessionReady) {
      return;
    }
  } catch {
    // Fall through to UI login.
  }

  await loginViaUiForm(page);
  if (!hostSessionReady) {
    throw new Error("Host dashboard shell did not appear after dev login");
  }
}

async function waitForDashboardShell(page: Page) {
  const loading = page.getByText(/Checking authentication|Loading your dashboard/i);
  if (await loading.isVisible({ timeout: 5000 }).catch(() => false)) {
    await expect(loading).toBeHidden({ timeout: 90000 });
  }
}

export async function ensureHostDashboard(page: Page, request: APIRequestContext) {
  await waitForDashboardShell(page);

  if (hostSessionReady && !(await isHostShellVisible(page))) {
    hostSessionReady = false;
  }

  if (hostSessionReady && (await isHostShellVisible(page))) {
    return;
  }

  if (await isHostShellVisible(page)) {
    hostSessionReady = true;
    return;
  }

  if (!page.url().includes("/dashboard")) {
    await loginAsDevHost(page, request);
    return;
  }

  await page.goto("/dashboard", { waitUntil: "domcontentloaded", timeout: 60000 });
  await waitForDashboardShell(page);
  if (await isHostShellVisible(page)) {
    hostSessionReady = true;
    return;
  }

  const onLogin = await page.locator("#email").isVisible({ timeout: 2000 }).catch(() => false);
  if (onLogin) {
    await loginAsDevHost(page, request);
    return;
  }

  await loginAsDevHost(page, request);
}

export async function openHostTab(page: Page, label: string) {
  const tabId = HOST_TAB_LABEL_TO_ID[label];
  if (!tabId) {
    throw new Error(`Unknown host dashboard tab label: ${label}`);
  }
  await page.goto(dashboardPathForTab(label), {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  if (tabId === "overview") {
    await expect(page).not.toHaveURL(/[?&]tab=/);
  } else {
    await expect(page).toHaveURL(new RegExp(`[?&]tab=${tabId}(&|$|#)`));
  }
  const tabButton = page.getByRole("button", { name: label, exact: true }).first();
  await expect(tabButton).toBeVisible({ timeout: 30000 });
}
