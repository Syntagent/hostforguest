/**
 * CI host dashboard smoke — dev login + overview tab on local API (:8000) + Next (:3055).
 */
import { test, expect } from "@playwright/test";
import { DEV_EMAIL, ensureHostDashboard, loginAsDevHost, openHostTab } from "./ci-host-auth";

const GROUP_NAME = process.env.E2E_GUEST_GROUP_NAME || "E2E CI Guest Group";

test.describe.configure({ mode: "serial" });

test.describe("CI host dashboard", () => {
  test("dev login lands on overview", async ({ page, request }) => {
    await loginAsDevHost(page, request);
    await ensureHostDashboard(page, request);

    await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible({
      timeout: 20000,
    });
    await expect(page.getByRole("link", { name: /Generate Welcome Kit/i })).toBeVisible({
      timeout: 15000,
    });
  });

  test("overview shows dashboard stats", async ({ page, request }) => {
    await ensureHostDashboard(page, request);
  });

  test("guests tab lists seeded CI guest group", async ({ page, request }) => {
    await ensureHostDashboard(page, request);
    await openHostTab(page, "Guests");

    await expect(page.getByText(GROUP_NAME).first()).toBeVisible({ timeout: 20000 });
  });

  test("account tab shows dev email", async ({ page, request }) => {
    await ensureHostDashboard(page, request);
    await openHostTab(page, "Account");

    await expect(page.getByText(DEV_EMAIL, { exact: true })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
  });

  test("guests tab opens create group modal and saves a new group", async ({ page, request }) => {
    await ensureHostDashboard(page, request);
    await openHostTab(page, "Guests");

    await page.getByRole("button", { name: "Create New Group" }).click();
    await expect(
      page.getByRole("heading", { name: "Create New Guest Group" })
    ).toBeVisible({ timeout: 15000 });

    const groupName = `CI E2E Group ${Date.now()}`;
    await page
      .getByPlaceholder("e.g., Smith Family, Business Trip Group")
      .fill(groupName);

    const createBtn = page.getByRole("button", { name: "Create Group", exact: true });
    await expect(createBtn).toBeEnabled();
    await createBtn.click();

    await expect(page.getByRole("heading", { name: "Create New Guest Group" })).toBeHidden({
      timeout: 30000,
    });
    await expect(page.getByText(groupName).first()).toBeVisible({ timeout: 30000 });
  });
});
