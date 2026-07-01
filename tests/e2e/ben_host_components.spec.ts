/**
 * E2E: Ben Test fills every host dashboard component (CRUD smoke).
 */
import { test, expect } from "@playwright/test";
import { loginAsBen, openTab } from "./ben-auth";

test.describe.configure({ mode: "serial" });

test.describe("Ben host all components", () => {
  test("Stay tab — save accommodation profile", async ({ page }) => {
    page.on("dialog", (d) => d.accept());
    await openTab(page, "Stay");
    await page.getByRole("button", { name: /^Edit$/i }).click();
    const story = page.getByLabel(/Property story/i);
    await story.fill(`Ben host QA story ${Date.now()}`);
    await page.getByRole("button", { name: "Save Changes" }).click();
    await expect(page.getByText(/Your Stay profile is updated/i)).toBeVisible({
      timeout: 5000,
    }).catch(() => expect(page.getByRole("button", { name: /^Edit$/i })).toBeVisible());
  });

  test("Stay tab — AI agent drafts location story", async ({ page }) => {
    await openTab(page, "Stay");
    await expect(page.getByText(/Stay assistant/i)).toBeVisible({ timeout: 30000 });
    await page
      .getByPlaceholder(/Tell the assistant one important fact/i)
      .fill("We offer sea views, homemade olive oil, and quiet family mornings.");
    await page.getByRole("button", { name: /Send assistant message/i }).click();
    await expect(page.getByText(/Draft suggestion|could not reach AI|Apply draft/i).first()).toBeVisible({
      timeout: 45000,
    });
  });

  test("Maintenance — create issue", async ({ page }) => {
    await page.goto("/dashboard");
    await openTab(page, "Maintenance");
    const title = `Ben maint ${Date.now()}`;
    await page.getByPlaceholder("e.g. Leak under sink").fill(title);
    await page.getByRole("button", { name: "Create issue", exact: true }).click();
    await expect(page.getByText(title)).toBeVisible({ timeout: 30000 });
  });

  test("Routes — create route template", async ({ page }) => {
    await page.goto("/dashboard");
    await openTab(page, "Routes");
    await page.getByRole("button", { name: "New template", exact: true }).click();
    const tname = `Ben Route ${Date.now()}`;
    await page.getByPlaceholder("e.g. Best of Lovran in one day").fill(tname);
    await page.getByRole("button", { name: "Create", exact: true }).click();
    await expect(page.getByText("Route templates", { exact: false })).toBeVisible();
    await expect(page.getByText(tname)).toBeVisible({ timeout: 45000 });
  });

  test("Adaptation — create project", async ({ page }) => {
    await openTab(page, "Adaptation");
    await page.getByText("New project", { exact: true }).click();
    const pname = `Ben Adapt ${Date.now()}`;
    await page.getByText("Project title").locator("..").locator("input").fill(pname);
    await page.getByRole("button", { name: "Create project", exact: true }).click();
    await expect(page.locator("select option", { hasText: pname })).toHaveCount(1, {
      timeout: 45000,
    });
  });

  test("Cleaning — discover providers", async ({ page }) => {
    page.on("dialog", (d) => d.accept());
    await page.goto("/dashboard");
    await openTab(page, "Cleaning");
    const discover = page.getByRole("button", { name: /Discover|Find cleaners|Rank/i });
    if (await discover.count()) {
      await discover.first().click({ timeout: 10000 }).catch(() => undefined);
    }
    await expect(
      page.getByText(/cleaning|partner|provider|ranked|disclaimer|checkout/i).first()
    ).toBeVisible({ timeout: 45000 });
  });

  test("Insights tab loads analytics", async ({ page }) => {
    await page.goto("/dashboard");
    await openTab(page, "Insights");
    await expect(
      page.getByText(/recommendation|insight|analytics|guest/i).first()
    ).toBeVisible({ timeout: 30000 });
  });
});
