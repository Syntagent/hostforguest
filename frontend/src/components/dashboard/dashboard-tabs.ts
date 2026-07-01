/** Host dashboard tab ids (internal). Nav labels differ (e.g. accommodation → "Stay"). */

export const DASHBOARD_TAB_IDS = [
  "overview",
  "accommodation",
  "channels",
  "groups",
  "attractions",
  "routes",
  "maintenance",
  "adaptation",
  "map",
  "discover",
  "cleaning",
  "insights",
] as const;

export type DashboardTab = (typeof DASHBOARD_TAB_IDS)[number];

export const DEFAULT_DASHBOARD_TAB: DashboardTab = "overview";

export const DASHBOARD_TAB_LABELS: Record<DashboardTab, string> = {
  overview: "Overview",
  accommodation: "Stay",
  channels: "Channels",
  groups: "Guests",
  attractions: "Attractions",
  routes: "Routes",
  maintenance: "Maintenance",
  adaptation: "Adaptation",
  map: "Map",
  discover: "Discover",
  cleaning: "Cleaning",
  insights: "Insights",
};

/** Friendly ?tab= aliases (lowercase) → internal id */
const TAB_URL_ALIASES: Record<string, DashboardTab> = {
  overview: "overview",
  accommodation: "accommodation",
  stay: "accommodation",
  channels: "channels",
  groups: "groups",
  guests: "groups",
  attractions: "attractions",
  routes: "routes",
  maintenance: "maintenance",
  adaptation: "adaptation",
  map: "map",
  discover: "discover",
  cleaning: "cleaning",
  insights: "insights",
};

export function isDashboardTab(value: string): value is DashboardTab {
  return (DASHBOARD_TAB_IDS as readonly string[]).includes(value);
}

export function parseDashboardTabParam(
  raw: string | null | undefined
): DashboardTab | null {
  if (!raw?.trim()) return null;
  const key = raw.trim().toLowerCase();
  return TAB_URL_ALIASES[key] ?? null;
}

/** Value for ?tab=; omit query param when overview (default). */
export function dashboardTabQueryValue(tab: DashboardTab): string | null {
  if (tab === DEFAULT_DASHBOARD_TAB) return null;
  return tab;
}

export function buildDashboardTabHref(
  pathname: string,
  tab: DashboardTab,
  existingSearch?: string
): string {
  const params = new URLSearchParams(existingSearch ?? "");
  const q = dashboardTabQueryValue(tab);
  if (q) params.set("tab", q);
  else params.delete("tab");
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}
