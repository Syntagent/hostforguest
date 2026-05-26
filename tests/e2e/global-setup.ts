import { chromium, type FullConfig } from "@playwright/test";
import fs from "fs";
import path from "path";
import { BEN_EMAIL, BEN_PASSWORD } from "./ben-auth";

const AUTH_FILE = path.join(__dirname, ".auth", "ben.json");

async function globalSetup(_config: FullConfig) {
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  const baseURL =
    process.env.PLAYWRIGHT_BASE_URL || "https://hostforguest.syntagent.com";
  const apiBase = process.env.PLAYWRIGHT_API_URL || baseURL;

  const loginRes = await fetch(`${apiBase}/api/v1/hosts/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: BEN_EMAIL, password: BEN_PASSWORD }),
  });
  if (!loginRes.ok) {
    throw new Error(`Ben login failed: ${loginRes.status} ${await loginRes.text()}`);
  }
  const data = (await loginRes.json()) as {
    session_token?: string;
    refresh_token?: string;
  };
  const sessionToken = data.session_token;
  const refreshToken = data.refresh_token;
  if (!sessionToken) {
    throw new Error("Ben login response missing session_token");
  }

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();
  await page.goto("/");
  await page.evaluate(
    ({ sessionToken, refreshToken }) => {
      localStorage.setItem("session_token", sessionToken);
      if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
    },
    { sessionToken, refreshToken: refreshToken || "" }
  );
  await page.goto("/dashboard");
  await page.waitForURL(/\/dashboard/, { timeout: 60000 });
  await context.storageState({ path: AUTH_FILE });
  await browser.close();
}

export default globalSetup;
