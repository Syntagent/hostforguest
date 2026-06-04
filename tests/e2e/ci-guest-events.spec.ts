/**
 * CI guest Events tab smoke — runs against local API (:8000) + Next (:3055).
 */
import { test, expect } from "@playwright/test";
import { openGuestApp, openGuestTab, waitForGuestShell } from "./ci-guest-auth";

test.describe.configure({ mode: "serial" });

test.describe("CI guest events", () => {
  test("events tab renders feed or empty state", async ({ page }) => {
    await openGuestApp(page);
    await waitForGuestShell(page);
    await openGuestTab(page, "Events");

    await expect(page.getByTestId("guest-events-tab")).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /Events for your stay|Događaji za vaš boravak/i })).toBeVisible({
      timeout: 15000,
    });

    const hasFeed = await page
      .getByTestId("guest-event-recommendation")
      .first()
      .isVisible()
      .catch(() => false);
    const empty = await page
      .getByText(/No event ideas right now|Open Discover/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasFeed || empty).toBeTruthy();
  });

  test("guest can save a synthetic event to plan", async ({ page, request }) => {
    const apiBase = (
      process.env.PLAYWRIGHT_API_URL ||
      process.env.PLAYWRIGHT_BASE_URL ||
      "http://127.0.0.1:8000"
    ).replace(/\/$/, "");
    const accessCode = process.env.E2E_GUEST_ACCESS_CODE;
    expect(accessCode).toBeTruthy();

    const event = {
      id: `ci-saved-event-${Date.now()}`,
      title: `CI saved event ${Date.now()}`,
      source: "feed",
      url: "https://example.com/ci-guest-event",
      plan_hint: "Synthetic event for CI saved-events flow.",
      cities: ["Lovran"],
    };

    const saveRes = await request.post(
      `${apiBase}/api/v1/guest-groups/access/${accessCode}/saved-events`,
      {
        data: {
          event_id: event.id,
          title: event.title,
          source: event.source,
          url: event.url,
          plan_hint: event.plan_hint,
          cities: event.cities,
        },
      }
    );
    expect(saveRes.ok()).toBeTruthy();

    await openGuestApp(page);
    await waitForGuestShell(page);
    await page.waitForResponse(
      (r) => r.url().includes("/saved-events") && r.status() === 200,
      { timeout: 30000 }
    );
    await openGuestTab(page, "Events");

    const savedIdea = page.getByTestId("events-saved-event-idea").filter({ hasText: event.title });
    await expect(savedIdea.first()).toBeVisible({ timeout: 20000 });
    await expect(savedIdea.first()).toContainText(event.plan_hint);

    await openGuestTab(page, "Plan");
    const planIdea = page.getByTestId("plan-event-idea").filter({ hasText: event.title });
    await expect(planIdea.first()).toBeVisible({ timeout: 20000 });

    await request.delete(
      `${apiBase}/api/v1/guest-groups/access/${accessCode}/saved-events/${event.id}`
    );
  });
});
