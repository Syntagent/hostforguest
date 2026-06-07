/** Host dashboard ?tab= helpers for Playwright (mirrors frontend dashboard-tabs.ts). */

export const HOST_TAB_LABEL_TO_ID: Record<string, string> = {
  Overview: "overview",
  Accommodation: "accommodation",
  Stay: "accommodation",
  Channels: "channels",
  Guests: "groups",
  Attractions: "attractions",
  Routes: "routes",
  Maintenance: "maintenance",
  Adaptation: "adaptation",
  Map: "map",
  Discover: "discover",
  Cleaning: "cleaning",
  Insights: "insights",
  Compliance: "compliance",
  Account: "account",
};

export function dashboardPathForTab(label: string): string {
  const tabId = HOST_TAB_LABEL_TO_ID[label];
  if (!tabId || tabId === "overview") return "/dashboard";
  return `/dashboard?tab=${tabId}`;
}
