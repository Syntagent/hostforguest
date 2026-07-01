/**
 * Debug dashboard groups tab for Playwright E2E.
 */
import { chromium } from "playwright";
import { randomBytes } from "crypto";
import { writeFileSync } from "fs";

const BASE = "https://hostforguest.syntagent.com";
const API = BASE;

async function main() {
  const email = `pw-${randomBytes(5).toString("hex")}@example.com`;
  const password = "PlaywrightPass123!";
  await fetch(`${API}/api/v1/hosts/register`, {
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
  const login = await fetch(`${API}/api/v1/hosts/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const { session_token, refresh_token } = await login.json();

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on("response", (r) => {
    if (r.url().includes("/api/v1/")) console.log(r.status(), r.request().method(), r.url());
  });

  await page.goto(`${BASE}/login`);
  await page.evaluate(({ session_token, refresh_token }) => {
    localStorage.setItem("session_token", session_token);
    if (refresh_token) localStorage.setItem("refresh_token", refresh_token);
  }, { session_token, refresh_token });

  await page.goto(`${BASE}/dashboard?tab=groups`, { waitUntil: "networkidle", timeout: 60000 });
  writeFileSync("/tmp/hfg-dashboard.html", await page.content());
  await page.screenshot({ path: "/tmp/hfg-dashboard.png", fullPage: true });
  console.log("URL:", page.url());
  console.log("Title:", await page.title());
  const buttons = await page.locator("button").allTextContents();
  console.log("Buttons:", buttons.slice(0, 20));
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
