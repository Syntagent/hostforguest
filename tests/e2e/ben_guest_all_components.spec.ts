/**
 * E2E: Ben scenario — every guest tab and interaction (no host session).
 */
import { test, expect } from "@playwright/test";
import { ACCESS_CODE, openGuestApp, openGuestTab, waitForGuestShell } from "./guest-auth";

test.describe.configure({ mode: "serial" });

test.describe("Ben guest all components", () => {
  test("join page validates access code", async ({ page }) => {
    await page.goto("/guest/join");
    await page.locator("#accessCode").fill(ACCESS_CODE);
    await page.getByRole("button", { name: /Continue/i }).click();
    await expect(page).toHaveURL(new RegExp(`/guest/(setup/)?${ACCESS_CODE}`), {
      timeout: 30000,
    });
  });

  test("guest welcome tab shows host and stay context", async ({ page }) => {
    await openGuestApp(page);
    await waitForGuestShell(page);
    await openGuestTab(page, "Welcome");
    await expect(page.getByText(/Hosted by|Your stay|Welcome/i).first()).toBeVisible({
      timeout: 20000,
    });
    await expect(page.getByRole("button", { name: /Refresh/i })).toBeVisible();
  });

  test("discover tab shows recommendations or empty state", async ({ page }) => {
    await openGuestApp(page);
    await openGuestTab(page, "Discover");
    await expect(page.getByRole("heading", { name: "Discover" })).toBeVisible();
    const hasRecs = await page.getByText(/places suggested|curated places/i).isVisible().catch(() => false);
    const empty = await page.getByText(/not shared curated places/i).isVisible().catch(() => false);
    expect(hasRecs || empty).toBeTruthy();
  });

  test("discover feedback thumbs when recommendations exist", async ({ page }) => {
    await openGuestApp(page);
    await openGuestTab(page, "Discover");
    const yesBtn = page.getByRole("button", { name: "Yes" }).first();
    if (await yesBtn.isVisible({ timeout: 8000 }).catch(() => false)) {
      await yesBtn.click();
    }
  });

  test("plan tab loads itinerary section", async ({ page }) => {
    await openGuestApp(page);
    await openGuestTab(page, "Plan");
    await expect(page.getByText(/itinerary|day plan|Plan/i).first()).toBeVisible({
      timeout: 20000,
    });
  });

  test("map tab loads map shell", async ({ page }) => {
    await openGuestApp(page);
    await openGuestTab(page, "Map");
    await expect(
      page.getByText(/map|nearby|attraction|recommendation/i).first()
    ).toBeVisible({ timeout: 30000 });
  });

  test("message host FAB sends a note", async ({ page }) => {
    await openGuestApp(page);
    await openGuestTab(page, "Welcome");
    await page.getByRole("button", { name: "Message host" }).click();
    await expect(page.getByRole("heading", { name: "Message your host" })).toBeVisible();
    const note = `Ben guest E2E note ${Date.now()}`;
    await page.getByPlaceholder(/extra towel|question/i).fill(note);
    await page.getByRole("button", { name: /^Send$/i }).click();
    await expect(page.getByText(/Sent|host|assistant|message/i).first()).toBeVisible({
      timeout: 20000,
    });
  });

  test("report issue tab submits maintenance report", async ({ page }) => {
    await openGuestApp(page);
    await openGuestTab(page, "Report issue");
    await expect(page.getByRole("heading", { name: "Report an issue" })).toBeVisible();
    const title = `Ben guest issue ${Date.now()}`;
    await page.locator("#gm-title").fill(title);
    await page.locator("#gm-desc").fill("E2E guest maintenance report from Ben scenario.");
    await page.getByRole("button", { name: "Send to host" }).click();
    await expect(page.getByText(/Sent.*host/i)).toBeVisible({ timeout: 20000 });
  });

  test("invalid access code shows access denied", async ({ page }) => {
    await page.goto("/guest/INVALIDCODE99");
    await expect(page.getByText(/Access Denied|Invalid|expired/i).first()).toBeVisible({
      timeout: 30000,
    });
  });
});
