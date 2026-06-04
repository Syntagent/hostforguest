import { type Page } from "@playwright/test";
import { openGuestTab } from "./guest-nav";
import { expectGuestWelcome, waitForGuestShell } from "./guest-shell";

export const ACCESS_CODE =
  process.env.BEN_GUEST_ACCESS_CODE || process.env.E2E_GUEST_ACCESS_CODE || "Q4EF3BFW";
export const GROUP_NAME =
  process.env.BEN_GUEST_GROUP_NAME || process.env.E2E_GUEST_GROUP_NAME || "";

export async function openGuestApp(page: Page, code: string = ACCESS_CODE) {
  await page.goto(`/guest/${code}`);
  await waitForGuestShell(page);
  await expectGuestWelcome(page, GROUP_NAME || undefined);
}

export { openGuestTab, waitForGuestShell };
