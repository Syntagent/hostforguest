import { expect, type Page } from "@playwright/test";

const TAB_ID_BY_LABEL: Record<string, string> = {
  Welcome: "welcome",
  "Your stay": "stay",
  Events: "events",
  Discover: "recommendations",
  Plan: "itinerary",
  Map: "map",
  "Report issue": "maintenance",
};

export async function openGuestTab(page: Page, label: string) {
  const tabId = TAB_ID_BY_LABEL[label] || label.toLowerCase().replace(/\s+/g, "-");
  const navButton = page.getByTestId(`app-nav-${tabId}`).first();

  if (await navButton.isVisible({ timeout: 4000 }).catch(() => false)) {
    await navButton.scrollIntoViewIfNeeded();
    await navButton.click({ timeout: 30000 });
    await page.waitForTimeout(400);
    return;
  }

  const more = page.getByRole("button", { name: /More dashboard sections/i });
  if (await more.isVisible({ timeout: 3000 }).catch(() => false)) {
    await more.click();
    const overflowNav = page.getByTestId(`app-nav-${tabId}`).first();
    await expect(overflowNav).toBeVisible({ timeout: 10000 });
    await overflowNav.click({ timeout: 30000 });
    await page.waitForTimeout(400);
    return;
  }

  const fallback = page.getByRole("button", { name: label, exact: true }).first();
  await fallback.scrollIntoViewIfNeeded();
  await fallback.click({ timeout: 30000 });
  await page.waitForTimeout(400);
}
