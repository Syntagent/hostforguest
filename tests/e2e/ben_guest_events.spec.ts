/**
 * E2E: Ben scenario — guest Events tab (realtime feed + welcome preview).
 */
import { test, expect } from "@playwright/test";
import { openGuestApp, openGuestTab, waitForGuestShell } from "./guest-auth";

const ACCESS_CODE = process.env.BEN_GUEST_ACCESS_CODE || "72HQ5TJL";

test.describe.configure({ mode: "serial" });

test.describe("Ben guest events", () => {
  test("events tab shows local events or empty state", async ({ page }) => {
    await openGuestApp(page);
    await waitForGuestShell(page);
    await openGuestTab(page, "Events");
    await expect(page.getByTestId("guest-events-tab")).toBeVisible({ timeout: 20000 });
    await expect(
      page.getByRole("heading", { name: /Events for your stay|Local events/i })
    ).toBeVisible({ timeout: 15000 });
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

  test("welcome may show events preview when feed has items", async ({ page }) => {
    await openGuestApp(page);
    await waitForGuestShell(page);
    await openGuestTab(page, "Welcome");
    const preview = page.getByTestId("guest-events-preview");
    if (await preview.isVisible({ timeout: 8000 }).catch(() => false)) {
      await expect(preview.getByRole("button", { name: "All events" })).toBeVisible();
      await preview.getByRole("button", { name: "All events" }).click();
      await expect(page.getByTestId("guest-events-tab")).toBeVisible({ timeout: 15000 });
    }
  });

  test("plan tab surfaces event ideas for itinerary building", async ({ page }) => {
    await openGuestApp(page);
    await waitForGuestShell(page);
    await openGuestTab(page, "Events");
    const saveButton = page.getByRole("button", { name: /Save to plan/i }).first();
    if (await saveButton.isVisible({ timeout: 10000 }).catch(() => false)) {
      await saveButton.click();
      await expect(page.getByRole("button", { name: /Saved to plan/i }).first()).toBeVisible();
    }
    await openGuestTab(page, "Plan");
    const ideas = page.getByTestId("plan-event-idea");
    if (await ideas.first().isVisible({ timeout: 10000 }).catch(() => false)) {
      await expect(page.getByRole("heading", { name: "Event ideas for your plan" })).toBeVisible();
      await expect(ideas.first()).toContainText(/match|fit|km|Near|Fits|Worth/i);
      await expect(page.getByRole("button", { name: /Remove from saved|Save to plan/i }).first()).toBeVisible();
    } else {
      await expect(page.getByRole("heading", { name: "Plan" })).toBeVisible();
    }
  });

  test("guest can ask host to place a saved event in the plan", async ({ page, request }) => {
    const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
    const event = {
      id: `saved-only-plan-request-${Date.now()}`,
      title: `Saved-only plan request ${Date.now()}`,
      source: "feed",
      url: "https://example.com/guest-plan-event",
      plan_hint: "Saved-only event keeps its planning hint.",
      cities: ["Lovran"],
    };

    const saveRes = await request.post(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events`,
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
    const welcomePreview = page.getByTestId("guest-events-preview");
    await expect(welcomePreview).toBeVisible({ timeout: 20000 });
    await expect(welcomePreview.getByText(event.title, { exact: true })).toBeVisible();
    await openGuestTab(page, "Plan");
    const matchingIdea = page.getByTestId("plan-event-idea").filter({ hasText: event.title });
    await expect(matchingIdea.first()).toBeVisible({ timeout: 20000 });
    await expect(matchingIdea.first()).toContainText(event.plan_hint);
    await expect(matchingIdea.first().getByRole("link", { name: "Open event details" })).toHaveAttribute("href", event.url);
    const askButton = matchingIdea.first().getByRole("button", { name: /Ask host to plan|Host asked/i });
    if (await askButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await askButton.click();
      await expect(matchingIdea.first()).toContainText(/asked your host|Host asked/i);
    } else {
      await matchingIdea.first().getByRole("button", { name: /^Day \d+$/ }).first().click();
      await expect(matchingIdea.first()).toContainText(/asked to plan this for Day|requested/i);
    }

    const savedRes = await request.get(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events`
    );
    expect(savedRes.ok()).toBeTruthy();
    const saved = (await savedRes.json()).saved_events?.find(
      (row: { event_id?: string }) => row.event_id === event.id
    );
    expect(["plan_request", "preferred_day"]).toContain(saved?.guest_action);

    await openGuestTab(page, "Events");
    await expect(page.getByTestId("guest-events-tab")).toBeVisible({ timeout: 20000 });
    const eventsIdea = page.getByTestId("events-saved-event-idea").filter({ hasText: event.title });
    await expect(eventsIdea).toHaveCount(1);
    await expect(eventsIdea.first()).toBeVisible({ timeout: 20000 });
    await expect(eventsIdea.first()).toContainText(event.plan_hint);
    await expect(eventsIdea.first().getByRole("button", { name: "Saved to plan" })).toBeVisible();
    await expect(eventsIdea.first().getByRole("link", { name: event.title })).toHaveAttribute("href", event.url);

    await openGuestTab(page, "Map");
    const mapIdea = page.getByTestId("map-saved-event-idea").filter({ hasText: event.title });
    await expect(mapIdea.first()).toBeVisible({ timeout: 20000 });
    await expect(mapIdea.first()).toContainText(event.plan_hint);
    await expect(mapIdea.first().getByRole("link", { name: "Event details" })).toHaveAttribute("href", event.url);
    await expect(mapIdea.first().getByRole("link", { name: "Open in Maps" })).toHaveAttribute(
      "href",
      /google\.com\/maps\/search/
    );

    await openGuestTab(page, "Discover");
    await expect(page.getByRole("heading", { name: "Discover" })).toBeVisible({ timeout: 15000 });
    const discoverIdea = page.getByTestId("discover-saved-event-idea").filter({ hasText: event.title });
    await expect(discoverIdea).toHaveCount(1);
    await expect(discoverIdea.first()).toBeVisible({ timeout: 20000 });
    await expect(discoverIdea.first()).toContainText(event.plan_hint);
    await expect(discoverIdea.first().getByText("Saved", { exact: true })).toBeVisible();
    await expect(discoverIdea.first().getByRole("link", { name: "Event details" })).toHaveAttribute("href", event.url);
    await expect(discoverIdea.first().getByRole("link", { name: "Open in Maps" })).toHaveAttribute(
      "href",
      /google\.com\/maps\/search/
    );

    await request.delete(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events/${event.id}`
    );
  });

  test("saved-only event survives from localStorage when saved-events API is empty", async ({ page, request }) => {
    const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
    const cacheKey = `tg_saved_events_${ACCESS_CODE}`;
    const event = {
      id: `saved-only-ls-cache-${Date.now()}`,
      title: `LS cache saved-only ${Date.now()}`,
      source: "feed",
      url: "https://example.com/ls-cache-event",
      plan_hint: "Persisted from localStorage metadata snapshot.",
      cities: ["Lovran"],
    };

    const saveRes = await request.post(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events`,
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
    await openGuestTab(page, "Events");
    const warm = page.getByTestId("events-saved-event-idea").filter({ hasText: event.title });
    await expect(warm.first()).toBeVisible({ timeout: 20000 });
    await expect(warm.first()).toContainText(event.plan_hint);

    const cached = await page.evaluate(
      ({ cacheKey, eventId }) => {
        const parsed = JSON.parse(localStorage.getItem(cacheKey) || "{}");
        return {
          version: parsed.v,
          ids: Array.isArray(parsed.ids) ? parsed.ids : [],
          row: parsed.details?.[eventId],
        };
      },
      { cacheKey, eventId: event.id }
    );
    expect(cached.version).toBe(1);
    expect(cached.ids).toContain(event.id);
    expect(cached.row?.plan_hint).toBe(event.plan_hint);

    await page.route("**/api/v1/guest-groups/access/*/saved-events", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, saved_event_ids: [], saved_events: [] }),
        });
        return;
      }
      await route.continue();
    });

    await page.reload();
    await waitForGuestShell(page);
    await openGuestTab(page, "Events");

    const eventsIdea = page.getByTestId("events-saved-event-idea").filter({ hasText: event.title });
    await expect(eventsIdea).toHaveCount(1);
    await expect(eventsIdea.first()).toBeVisible({ timeout: 20000 });
    await expect(eventsIdea.first()).toContainText(event.plan_hint);
    await expect(eventsIdea.first().getByRole("button", { name: "Saved to plan" })).toBeVisible();
    await expect(eventsIdea.first().getByRole("link", { name: event.title })).toHaveAttribute("href", event.url);

    await request.delete(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events/${event.id}`
    );
  });

  test("guest sees when host marks saved event planned", async ({ page, request }) => {
    const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
    const event = {
      id: `saved-only-visible-to-guest-${Date.now()}`,
      title: `Saved-only planned event ${Date.now()}`,
      source: "feed",
    };

    const saveRes = await request.post(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events`,
      {
        data: { event_id: event.id, title: event.title, source: event.source },
      }
    );
    expect(saveRes.ok()).toBeTruthy();

    const loginRes = await request.post(`${apiBase}/api/v1/hosts/login`, {
      data: {
        email: process.env.BEN_TEST_EMAIL || "benediktperak@gmail.com",
        password: process.env.BEN_TEST_PASSWORD || "Ben@Host1",
      },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).session_token;
    const groupsRes = await request.get(`${apiBase}/api/v1/guest-groups/host`, {
      headers: { "X-Session-Token": token },
    });
    expect(groupsRes.ok()).toBeTruthy();
    const group = (await groupsRes.json()).find(
      (row: { access_code?: string; group_name?: string }) =>
        row.access_code === ACCESS_CODE || row.group_name === "Ben Scenario Family 2026"
    );
    expect(group?.id).toBeTruthy();
    const plannedRes = await request.put(
      `${apiBase}/api/v1/guest-groups/${group.id}/saved-events/${event.id}`,
      {
        headers: { "X-Session-Token": token },
        data: { host_status: "planned", host_note: "E2E planned for guest visibility" },
      }
    );
    expect(plannedRes.ok()).toBeTruthy();

    await openGuestApp(page);
    await waitForGuestShell(page);
    await openGuestTab(page, "Plan");
    const matchingIdea = page.getByTestId("plan-event-idea").filter({ hasText: event.title });
    await expect(matchingIdea.first()).toBeVisible({ timeout: 20000 });
    await expect(matchingIdea.first().getByText("Host planned")).toBeVisible();
    await expect(matchingIdea.first()).toContainText("E2E planned for guest visibility");
  });

  test("guest sees when host adds saved event to itinerary", async ({ page, request }) => {
    const apiBase = process.env.PLAYWRIGHT_API_URL || "https://hostforguest.syntagent.com";
    const loginRes = await request.post(`${apiBase}/api/v1/hosts/login`, {
      data: {
        email: process.env.BEN_TEST_EMAIL || "benediktperak@gmail.com",
        password: process.env.BEN_TEST_PASSWORD || "Ben@Host1",
      },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).session_token;
    const headers = { "X-Session-Token": token };

    const groupsRes = await request.get(`${apiBase}/api/v1/guest-groups/host`, { headers });
    expect(groupsRes.ok()).toBeTruthy();
    const group = (await groupsRes.json()).find(
      (row: { access_code?: string; group_name?: string }) =>
        row.access_code === ACCESS_CODE || row.group_name === "Ben Scenario Family 2026"
    );
    expect(group?.id).toBeTruthy();

    const existingItineraryRes = await request.get(
      `${apiBase}/api/v1/itineraries/guest/${ACCESS_CODE}/itinerary`
    );
    expect(existingItineraryRes.ok()).toBeTruthy();
    let itinerary = await existingItineraryRes.json();
    if (!itinerary) {
      const today = new Date().toISOString().slice(0, 10);
      const end = new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
      const createItineraryRes = await request.post(
        `${apiBase}/api/v1/itineraries/?guest_group_id=${group.id}`,
        {
          headers,
          data: {
            title: "Ben Guest Event Plan",
            description: "Created for guest event planning verification",
            base_location: "Lovran, Croatia",
            start_date: today,
            end_date: end,
            is_template: false,
            pace: "moderate",
            budget_level: "medium",
          },
        }
      );
      expect(createItineraryRes.ok()).toBeTruthy();
      itinerary = await createItineraryRes.json();
    }

    let day = itinerary.day_plans?.[0];
    if (!day) {
      const createDayRes = await request.post(
        `${apiBase}/api/v1/itineraries/${itinerary.id}/day-plans`,
        {
          headers,
          data: {
            day_number: 1,
            date: new Date().toISOString().slice(0, 10),
            title: "Guest event ideas",
            theme: "Guest-picked events",
          },
        }
      );
      expect(createDayRes.ok()).toBeTruthy();
      day = await createDayRes.json();
    }
    expect(day?.id).toBeTruthy();

    const event = {
      id: `saved-only-added-to-itinerary-${Date.now()}`,
      title: `Added to itinerary event ${Date.now()}`,
      source: "feed",
    };
    const saveRes = await request.post(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events`,
      { data: { event_id: event.id, title: event.title, source: event.source } }
    );
    expect(saveRes.ok()).toBeTruthy();
    const intentRes = await request.patch(
      `${apiBase}/api/v1/guest-groups/access/${ACCESS_CODE}/saved-events/${event.id}`,
      {
        data: {
          guest_action: "preferred_day",
          preferred_day_plan_id: day.id,
          preferred_day_number: day.day_number || 1,
          preferred_day_title: day.theme || day.title || "Guest-picked events",
        },
      }
    );
    expect(intentRes.ok()).toBeTruthy();
    const convertRes = await request.post(
      `${apiBase}/api/v1/guest-groups/${group.id}/saved-events/${event.id}/itinerary-activity`,
      {
        headers,
        data: { day_plan_id: day.id, scheduled_start_time: "18:00" },
      }
    );
    expect(convertRes.ok()).toBeTruthy();

    await openGuestApp(page);
    await waitForGuestShell(page);
    await openGuestTab(page, "Plan");
    const matchingIdea = page.getByTestId("plan-event-idea").filter({ hasText: event.title });
    await expect(matchingIdea.first()).toBeVisible({ timeout: 20000 });
    await expect(matchingIdea.first().getByText("In itinerary")).toBeVisible();
    await expect(matchingIdea.first()).toContainText("Your host added this event to the itinerary");
    await expect(matchingIdea.first()).toContainText(/scheduled/i);
    const itineraryActivity = page.getByTestId("itinerary-activity").filter({ hasText: event.title });
    await expect(itineraryActivity.first()).toBeVisible({ timeout: 20000 });
    await expect(itineraryActivity.first()).toContainText("Guest event request");
  });
});
