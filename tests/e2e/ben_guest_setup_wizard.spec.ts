/**
 * E2E: brand-new guest group — full onboarding wizard then dashboard.
 */
import { test, expect } from "@playwright/test";
import { BEN_EMAIL, BEN_PASSWORD } from "./ben-auth";

let setupCode: string;

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
  const login = await request.post(`${apiBase}/api/v1/hosts/login`, {
    data: { email: BEN_EMAIL, password: BEN_PASSWORD },
  });
  expect(login.ok()).toBeTruthy();
  const token = (await login.json()).session_token as string;
  const groupName = `Ben Setup Wizard ${Date.now()}`;
  const created = await request.post(`${apiBase}/api/v1/guest-groups/`, {
    headers: { "X-Session-Token": token, "Content-Type": "application/json" },
    data: {
      group_name: groupName,
      group_size: 2,
      lead_guest_name: "Test Guest",
      lead_guest_email: "setup-guest@example.com",
    },
  });
  expect(created.ok()).toBeTruthy();
  const body = await created.json();
  setupCode = body.access_code as string;
  expect(setupCode?.length).toBeGreaterThan(5);
});

test.describe("Guest setup wizard", () => {
  test("new guest completes wizard and lands on guide", async ({ page }) => {
    await page.goto("/guest/join");
    await page.locator("#accessCode").fill(setupCode);
    await page.getByRole("button", { name: /Continue/i }).click();
    await expect(page).toHaveURL(new RegExp(`/guest/setup/${setupCode}`), { timeout: 30000 });
    await expect(page.getByRole("heading", { name: "Set up your stay" })).toBeVisible();

    await page.getByLabel(/first name/i).fill("E2E");
    await page.getByLabel(/last name/i).fill("Guest");
    await page.getByLabel(/email/i).fill(`e2e.guest.${Date.now()}@example.com`);
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Continue" }).click();

    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByText("Food & wine").click();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Save & open my guide" }).click();

    await expect(page).toHaveURL(new RegExp(`/guest/${setupCode}`), { timeout: 45000 });
    await expect(page.getByRole("button", { name: "Welcome", exact: true })).toBeVisible({
      timeout: 30000,
    });
  });
});
