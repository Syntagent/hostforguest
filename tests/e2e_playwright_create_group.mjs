/**
 * Browser E2E: host can create a guest group on production.
 * Run: node tests/e2e_playwright_create_group.mjs
 */
import { chromium } from "playwright";
import { randomBytes } from "crypto";

const BASE = (process.env.HOSTFORGUEST_PUBLIC_URL || "https://hostforguest.syntagent.com").replace(/\/$/, "");
const API = (process.env.HOSTFORGUEST_API_URL || BASE).replace(/\/$/, "");

async function apiRegisterAndLogin() {
  const email = `pw-${randomBytes(5).toString("hex")}@example.com`;
  const password = "PlaywrightPass123!";
  const reg = await fetch(`${API}/api/v1/hosts/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      first_name: "PW",
      last_name: "Test",
      address: "1 St",
      city: "Lovran",
      country: "Croatia",
    }),
  });
  if (!reg.ok) throw new Error(`register failed: ${reg.status} ${await reg.text()}`);

  const login = await fetch(`${API}/api/v1/hosts/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!login.ok) throw new Error(`login failed: ${login.status}`);
  const { session_token } = await login.json();
  return { email, session_token };
}

async function main() {
  const { email, session_token } = await apiRegisterAndLogin();
  const groupName = `PW Group ${randomBytes(3).toString("hex")}`;

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();

  await page.goto(`${BASE}/login`);
  await page.evaluate((token) => {
    localStorage.setItem("session_token", token);
  }, session_token);

  await page.goto(`${BASE}/dashboard`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Guests" }).click();
  await page.getByRole("button", { name: "Create New Group" }).click({ timeout: 20000 });
  await page.getByPlaceholder("e.g., Smith Family, Business Trip Group").fill(groupName);
  await page.locator('input[type="number"]').fill("3");
  await page.getByRole("button", { name: "Create Group" }).click();

  await page.getByText(groupName).waitFor({ state: "visible", timeout: 15000 });
  await browser.close();

  console.log(`OK browser create group: ${groupName} (${email})`);
}

main().catch((err) => {
  console.error("FAIL:", err.message || err);
  process.exit(1);
});
