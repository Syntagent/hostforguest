"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BentoGrid } from "@/components/ui/bento-grid";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AppLayout } from "@/components/layout/app-layout";
import { AttractionDetailSheet } from "@/components/guest/AttractionDetailSheet";
import {
  AlertTriangle,
  Compass,
  Handshake,
  Landmark,
  Map,
  MapPin,
  PartyPopper,
  Sparkles,
  CalendarDays,
  UtensilsCrossed,
  Trees,
  ShoppingBag,
  Search,
  Waves,
  Wrench,
  ThumbsUp,
  ThumbsDown,
  MessageCircle,
  CheckCircle2,
  Leaf,
  Quote,
} from "lucide-react";
import {
  guestGroupsApi,
  recommendationsApi,
  itinerariesApi,
  guestMaintenanceApi,
  mapsUrlForAttraction,
  openAttractionInMaps,
  mapsUrlForItineraryActivity,
  GuestGroup,
  Recommendation,
  Itinerary,
  type Attraction,
  type GuestHostOfferingsPayload,
  type GuestPreferenceRecord,
  type GuestTestimonialEntry,
  type HostFavoriteLocalSpot,
  type ItineraryActivity,
} from "@/lib/api";

const GuestMap = dynamic(
  () =>
    import("@/components/guest/GuestMap").then((m) => ({ default: m.GuestMap })),
  { ssr: false, loading: () => <div className="skeleton h-[42vh] w-full rounded-2xl md:h-[48vh]" /> }
);

interface GuestInterfaceProps {
  accessCode: string;
  className?: string;
}

type GuestTab = "welcome" | "recommendations" | "itinerary" | "map" | "maintenance";

export const GuestInterface: React.FC<GuestInterfaceProps> = ({ 
  accessCode, 
  className 
}) => {
  const router = useRouter();
  const [guestGroup, setGuestGroup] = useState<GuestGroup | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [hostOfferings, setHostOfferings] = useState<GuestHostOfferingsPayload | null>(null);
  const [guestPreferences, setGuestPreferences] = useState<GuestPreferenceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<GuestTab>("welcome");
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailRec, setDetailRec] = useState<Recommendation | null>(null);
  const [recFeedback, setRecFeedback] = useState<Record<string, 1 | 5>>({});

  const feedbackStorageKey = useMemo(() => `tg_rec_fb_${accessCode}`, [accessCode]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(feedbackStorageKey);
      if (raw) {
        const parsed = JSON.parse(raw) as Record<string, 1 | 5>;
        if (parsed && typeof parsed === "object") setRecFeedback(parsed);
      }
    } catch {
      /* ignore */
    }
  }, [feedbackStorageKey]);

  const loadGuestData = useCallback(async (mode: "initial" | "refresh" = "initial") => {
    if (mode === "initial") {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    setError(null);
    let pendingSetupRedirect = false;

    try {
      const groupResponse = await guestGroupsApi.getByAccessCode(accessCode);
      if (!groupResponse.success) {
        throw new Error(groupResponse.error || "Invalid access code");
      }
      setGuestGroup(groupResponse.data!);

      const prefsResponse = await guestGroupsApi.getGuestPreferences(accessCode);
      if (
        prefsResponse.success &&
        prefsResponse.data &&
        prefsResponse.data.length === 0
      ) {
        pendingSetupRedirect = true;
        router.replace(`/guest/setup/${accessCode}`);
        return;
      }
      if (prefsResponse.success && prefsResponse.data) {
        setGuestPreferences(prefsResponse.data);
      } else {
        setGuestPreferences([]);
      }

      const [recommendationsResponse, historyResponse, itinerariesResponse, hostOffResponse] =
        await Promise.all([
          recommendationsApi.getForGroup(accessCode),
          recommendationsApi.getHistory(accessCode),
          itinerariesApi.getForGroup(accessCode),
          guestGroupsApi.getHostOfferings(accessCode),
        ]);

      const recs =
        recommendationsResponse.success && recommendationsResponse.data
          ? recommendationsResponse.data
          : [];
      setRecommendations(recs);

      setRecFeedback((prev) => {
        const fromServer: Record<string, 1 | 5> = {};
        const applyFeedback = (rows: Recommendation[]) => {
          for (const r of rows) {
            const fr = r.feedback_rating;
            if (fr === 1 || fr === 5) fromServer[r.id] = fr;
          }
        };
        applyFeedback(recs);
        if (historyResponse.success && historyResponse.data) {
          applyFeedback(historyResponse.data);
        }
        const merged = { ...prev, ...fromServer };
        try {
          localStorage.setItem(feedbackStorageKey, JSON.stringify(merged));
        } catch {
          /* ignore */
        }
        return merged;
      });

      if (itinerariesResponse.success && itinerariesResponse.data) {
        setItineraries([itinerariesResponse.data]);
      } else {
        setItineraries([]);
      }

      if (
        hostOffResponse.success &&
        hostOffResponse.data &&
        hostOffResponse.data.success &&
        hostOffResponse.data.host_offerings
      ) {
        setHostOfferings(hostOffResponse.data.host_offerings);
      } else {
        setHostOfferings(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      if (!pendingSetupRedirect) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [accessCode, router, feedbackStorageKey]);

  useEffect(() => {
    void loadGuestData("initial");
  }, [loadGuestData]);

  const headerSubtitle = useMemo(() => {
    const name = guestGroup?.group_name?.trim();
    switch (activeTab) {
      case "welcome":
        return "Your curated Croatian journey";
      case "recommendations":
        return name
          ? `Places and experiences picked for ${name}`
          : "Places and experiences from your host";
      case "itinerary":
        return name
          ? `Day-by-day ideas for ${name}`
          : "Day-by-day ideas from your host";
      case "map":
        return name
          ? `Where recommended spots are — ${name}`
          : "Where your recommended spots are";
      case "maintenance":
        return "Something at the property needs attention? Tell your host.";
      default:
        return "Your curated Croatian journey";
    }
  }, [activeTab, guestGroup?.group_name]);

  const openRecommendationDetail = useCallback((rec: Recommendation) => {
    setDetailRec(rec);
    setDetailOpen(true);
  }, []);

  const submitRecFeedback = useCallback(
    async (recId: string, rating: 1 | 5) => {
      const res = await recommendationsApi.provideFeedback(accessCode, {
        recommendation_id: recId,
        rating,
      });
      if (!res.success) return;
      setRecFeedback((prev) => {
        const next = { ...prev, [recId]: rating };
        try {
          localStorage.setItem(feedbackStorageKey, JSON.stringify(next));
        } catch {
          /* ignore */
        }
        return next;
      });
    },
    [accessCode, feedbackStorageKey]
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-background px-4 py-8 md:px-6 lg:px-8">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <div className="skeleton h-24 rounded-3xl md:h-28" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="skeleton h-48 rounded-3xl md:h-56" />
            <div className="skeleton h-48 rounded-3xl md:h-56" />
            <div className="skeleton h-48 rounded-3xl md:h-56" />
          </div>
          <p className="text-center text-sm text-muted-foreground">
            Loading your guide… this only takes a moment.
          </p>
        </div>
      </div>
    );
  }

  if (error || !guestGroup) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-600 via-pink-600 to-purple-800">
        <div className="text-center text-white max-w-md mx-auto px-6">
          <div className="mb-6 flex justify-center">
            <AlertTriangle className="h-14 w-14" />
          </div>
          <h1 className="text-2xl font-bold mb-4">Access Denied</h1>
          <p className="text-red-200 mb-6">
            {error || 'Invalid or expired access code. Please check with your host.'}
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Button variant="outline" onClick={() => window.location.reload()}>
              Try again
            </Button>
            <Link
              href="/guest/join"
              className="inline-flex min-h-11 items-center justify-center rounded-2xl border-2 border-white/80 px-5 py-2.5 text-center font-semibold text-white transition-colors hover:bg-white/15 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-transparent"
            >
              Use a different code
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <AppLayout
        className={cn("min-h-screen", className)}
        title={`Welcome${guestGroup.group_name ? `, ${guestGroup.group_name}` : ""}`}
        subtitle={headerSubtitle}
        navItems={[
          { id: "welcome", label: "Welcome", icon: <Handshake /> },
          { id: "recommendations", label: "Discover", icon: <Sparkles /> },
          { id: "itinerary", label: "Plan", icon: <CalendarDays /> },
          { id: "map", label: "Map", icon: <Map /> },
          { id: "maintenance", label: "Report issue", icon: <Wrench /> },
        ]}
        activeItem={activeTab}
        onSelectItem={(id) => setActiveTab(id as typeof activeTab)}
        headerActions={
          <Button
            variant="outline"
            disabled={refreshing}
            onClick={() => void loadGuestData("refresh")}
          >
            {refreshing ? "Refreshing…" : "Refresh"}
          </Button>
        }
      >
        {activeTab === "welcome" && (
          <WelcomeTab
            key="welcome"
            guestGroup={guestGroup}
            hostOfferings={hostOfferings}
            guestPreferences={guestPreferences}
            accessCode={accessCode}
            recommendationCount={recommendations.length}
            hasItinerary={itineraries.length > 0}
            onContinue={() => setActiveTab("recommendations")}
            onViewItinerary={() => setActiveTab("itinerary")}
            onNavigate={setActiveTab}
          />
        )}

        {activeTab === "recommendations" && (
          <RecommendationsTab
            key="recommendations"
            guestGroup={guestGroup}
            recommendations={recommendations}
            onNavigate={setActiveTab}
            onOpenDetail={openRecommendationDetail}
            recFeedback={recFeedback}
            onFeedback={submitRecFeedback}
          />
        )}

        {activeTab === "itinerary" && (
          <ItineraryTab
            key="itinerary"
            guestGroup={guestGroup}
            itineraries={itineraries}
            onNavigate={setActiveTab}
            accessCode={accessCode}
          />
        )}

        {activeTab === "map" && (
          <MapTab
            key="map"
            guestGroup={guestGroup}
            recommendations={recommendations}
            hostOfferings={hostOfferings}
            onNavigate={setActiveTab}
            onOpenRecommendationDetail={openRecommendationDetail}
          />
        )}

        {activeTab === "maintenance" && (
          <GuestMaintenanceReportPanel key="maintenance" accessCode={accessCode} />
        )}
      </AppLayout>

      <AttractionDetailSheet
        open={detailOpen}
        onOpenChange={setDetailOpen}
        recommendation={detailRec}
      />

      <GuestMessageFab
        accessCode={accessCode}
        hostOfferings={hostOfferings}
        activeTab={activeTab}
      />
    </>
  );
};

function welcomeCardActivate(
  e: React.KeyboardEvent,
  action: () => void
) {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    action();
  }
}

function formatCategoryLabel(key: string): string {
  if (key === "all") return "All";
  if (!key) return "Other";
  return key.charAt(0).toUpperCase() + key.slice(1).toLowerCase();
}

function timeOfDayGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function stayContextChips(guestGroup: GuestGroup): { label: string; key: string }[] {
  const chips: { label: string; key: string }[] = [];
  const inStr = guestGroup.check_in_date;
  const outStr = guestGroup.check_out_date;
  if (!inStr || !outStr) return chips;
  const inD = new Date(inStr);
  const outD = new Date(outStr);
  const now = new Date();
  if (Number.isNaN(inD.getTime()) || Number.isNaN(outD.getTime())) return chips;
  const dayMs = 86400000;
  const start = new Date(inD.getFullYear(), inD.getMonth(), inD.getDate());
  const end = new Date(outD.getFullYear(), outD.getMonth(), outD.getDate());
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (today >= start && today <= end) {
    const dayNum = Math.floor((today.getTime() - start.getTime()) / dayMs) + 1;
    const total = Math.max(1, Math.floor((end.getTime() - start.getTime()) / dayMs) + 1);
    chips.push({ key: "day", label: `Day ${dayNum} of ${total}` });
    const left = Math.ceil((end.getTime() - today.getTime()) / dayMs);
    if (left >= 0) {
      chips.push({
        key: "left",
        label: left === 0 ? "Last day of stay" : `${left} day${left === 1 ? "" : "s"} left`,
      });
    }
  }
  return chips;
}

function activityTimeLabel(activity: ItineraryActivity): string {
  const raw = activity.scheduled_start_time || activity.start_time;
  if (!raw) return "—";
  try {
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return String(raw);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return String(raw);
  }
}

function activityDisplayTitle(activity: ItineraryActivity): string {
  return (
    activity.title?.trim() ||
    activity.attraction?.name?.trim() ||
    activity.location_name?.trim() ||
    "Activity"
  );
}

function seasonalPickBadge(attraction?: Attraction | null): string | null {
  const months = attraction?.best_months;
  if (!months?.length) return null;
  const now = new Date().getMonth() + 1;
  return months.includes(now) ? "Great this month" : null;
}

function parseGuestTestimonials(
  raw: GuestTestimonialEntry[] | undefined
): Array<{ text: string; author?: string; rating?: number }> {
  if (!raw?.length) return [];
  const out: Array<{ text: string; author?: string; rating?: number }> = [];
  for (const t of raw) {
    if (typeof t === "string") {
      const text = t.trim();
      if (text) out.push({ text });
      continue;
    }
    if (!t || typeof t !== "object") continue;
    const o = t as Record<string, unknown>;
    const textKeys = ["quote", "text", "message", "body", "review", "content"] as const;
    let text = "";
    for (const k of textKeys) {
      const v = o[k];
      if (typeof v === "string" && v.trim()) {
        text = v.trim();
        break;
      }
    }
    if (!text) continue;
    const authorKeys = ["author", "name", "guest_name", "from", "by"] as const;
    let author: string | undefined;
    for (const k of authorKeys) {
      const v = o[k];
      if (typeof v === "string" && v.trim()) {
        author = v.trim();
        break;
      }
    }
    const r = o.rating;
    const rating =
      typeof r === "number" && Number.isFinite(r) && r >= 0 && r <= 5 ? r : undefined;
    out.push({ text, author, rating });
  }
  return out;
}

function normalizeFavoriteLocalSpots(raw: unknown): HostFavoriteLocalSpot[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter((item): item is HostFavoriteLocalSpot => {
    if (!item || typeof item !== "object") return false;
    const o = item as HostFavoriteLocalSpot;
    const n = typeof o.name === "string" ? o.name.trim() : "";
    const d = typeof o.description === "string" ? o.description.trim() : "";
    return Boolean(n || d);
  });
}

function mapsSearchUrlForFavoriteSpot(
  spot: HostFavoriteLocalSpot,
  city?: string | null
): string {
  const name = spot.name?.trim();
  const q = [name, city?.trim()].filter((x): x is string => Boolean(x?.length)).join(" ");
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q || name || "near me")}`;
}

/** Place name from one line like "Welcome to Oprić!" or "Welcome to Villa Maria in Oprić!". */
function placeFromWelcomeHeadlineLine(line: string): string | null {
  const m = line.match(/^welcome\s+to\s+(.+?)!\s*$/i);
  if (!m) return null;
  const inner = m[1].trim();
  if (/\s+in\s+/i.test(inner)) {
    const tail = inner.split(/\s+in\s+/i).pop()?.trim();
    return tail && tail.length >= 2 ? tail : null;
  }
  if (/^(our|the|my)\s+/i.test(inner)) return null;
  return inner.length >= 2 ? inner : null;
}

function SnapScrollRow({
  children,
  count,
}: {
  children: React.ReactNode;
  count: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [idx, setIdx] = useState(0);
  const onScroll = () => {
    const el = ref.current;
    if (!el || count <= 0) return;
    const scroll = el.scrollLeft;
    const w = el.offsetWidth || 1;
    const cardApprox = w * 0.84 + 16;
    const i = Math.min(count - 1, Math.max(0, Math.round(scroll / cardApprox)));
    setIdx(i);
  };
  return (
    <div className="relative">
      <div
        ref={ref}
        onScroll={onScroll}
        className="relative flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {children}
      </div>
      <div
        className="pointer-events-none absolute inset-y-0 right-0 top-0 z-[1] w-10 bg-gradient-to-l from-background via-background/80 to-transparent md:hidden"
        aria-hidden
      />
      {count > 1 ? (
        <p className="mt-1 text-center text-xs text-muted-foreground">
          {idx + 1} / {count} · swipe for more
        </p>
      ) : null}
    </div>
  );
}

const WelcomeTab: React.FC<{
  guestGroup: GuestGroup;
  hostOfferings: GuestHostOfferingsPayload | null;
  guestPreferences: GuestPreferenceRecord[];
  accessCode: string;
  recommendationCount: number;
  hasItinerary: boolean;
  onContinue: () => void;
  onViewItinerary: () => void;
  onNavigate: (tab: GuestTab) => void;
}> = ({
  guestGroup,
  hostOfferings,
  guestPreferences,
  accessCode,
  recommendationCount,
  hasItinerary,
  onContinue,
  onViewItinerary,
  onNavigate,
}) => {
  const hi = hostOfferings?.host_info;
  const si = hostOfferings?.stay_info;
  const city =
    si?.city?.trim() || hi?.city || hostOfferings?.location_info?.city;
  const propertyName = si?.property_name?.trim();
  const propertyAddress = si?.address?.trim();
  const hostWelcomeRaw = hi?.welcome_message?.trim() || "";
  const firstWelcomeLine = hostWelcomeRaw.split("\n")[0]?.trim() || "";
  const welcomeIsShortTitle = /^welcome\s+to\s+.+\s*!$/i.test(firstWelcomeLine);
  const placeFromWelcome = welcomeIsShortTitle
    ? placeFromWelcomeHeadlineLine(firstWelcomeLine)
    : null;
  /**
   * stay_info.city comes from property address / profile (Oprić). The host welcome line may still
   * say the business city (Rijeka). If they disagree, trust the API — do not let the headline win.
   */
  const displayPlace =
    city &&
    placeFromWelcome &&
    placeFromWelcome.trim().toLowerCase() !== city.trim().toLowerCase()
      ? city
      : placeFromWelcome || city || hi?.city?.trim() || "";
  const welcomeHeadlineMatchesPlace = Boolean(
    placeFromWelcome &&
      displayPlace &&
      placeFromWelcome.trim().toLowerCase() === displayPlace.trim().toLowerCase(),
  );
  /** Drop leading "Welcome to …!" so we can show geo-accurate headline without duplicating a wrong city. */
  const hostWelcomeBody = (() => {
    if (!hostWelcomeRaw) return "";
    const t = hostWelcomeRaw.replace(/^\s*welcome\s+to\s+[^!\n]+!\s*/i, "").trim();
    return t;
  })();
  const welcomeTitle =
    propertyName && displayPlace
      ? `Welcome to ${propertyName} in ${displayPlace}!`
      : welcomeIsShortTitle && firstWelcomeLine && welcomeHeadlineMatchesPlace
        ? firstWelcomeLine
        : displayPlace
          ? `Welcome to ${displayPlace}!`
          : hostWelcomeRaw || "Dobro došli u Hrvatsku";
  const stayHeadline = propertyName
    ? displayPlace
      ? `${propertyName} · ${displayPlace}`
      : propertyName
    : displayPlace
      ? `Your stay in ${displayPlace}`
      : "Your stay";
  const hostLine = hi?.name
    ? hi.broader_city &&
        displayPlace &&
        hi.broader_city.trim().toLowerCase() !== displayPlace.trim().toLowerCase()
      ? `Hosted by ${hi.name} — you're staying in ${displayPlace} (${hi.broader_city} area)`
      : `Hosted by ${hi.name}`
    : null;
  const stayChips = stayContextChips(guestGroup);
  const primaryPref = guestPreferences[0];
  const amenityChips = (si?.amenities || []).filter(
    (a): a is string => typeof a === "string" && a.trim().length > 0
  );
  const favoriteSpots = normalizeFavoriteLocalSpots(
    hostOfferings?.recommendations?.attractions
  );
  const guestTestimonialBlocks = parseGuestTestimonials(
    hostOfferings?.profile_extras?.guest_testimonials
  ).slice(0, 3);

  return (
    <div className="space-y-4">
      <div className="section-shell relative overflow-hidden px-4 py-6 md:px-6 md:py-7">
        <div
          className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/12 via-teal-500/8 to-emerald-500/12"
          aria-hidden
        />
        <div className="relative">
          <span className="sr-only">
            Group: {guestGroup.group_name?.trim() || "guest"}
          </span>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
            {timeOfDayGreeting()} · Your stay
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-foreground md:text-3xl">
            {welcomeTitle}
          </h2>
          <p className="mt-1 text-sm font-semibold text-foreground">{stayHeadline}</p>
          {hostLine ? (
            <p className="mt-0.5 text-sm font-medium text-primary">{hostLine}</p>
          ) : null}
          {hostWelcomeBody ? (
            <p className="mt-3 max-w-2xl text-pretty text-sm leading-relaxed text-foreground/90 md:text-base">
              {hostWelcomeBody}
            </p>
          ) : null}
          <p className="mt-3 max-w-2xl text-pretty text-sm text-muted-foreground md:text-base">
            Everything here is for your time at this property: local tips, ideas nearby, and a
            way to reach your host. Open{" "}
            <span className="font-medium text-foreground">Discover</span> for places,{" "}
            <span className="font-medium text-foreground">Plan</span> for day plans,{" "}
            <span className="font-medium text-foreground">Map</span> for directions, and{" "}
            <span className="font-medium text-foreground">Report issue</span> if something at the
            accommodation needs attention.
          </p>

          {propertyAddress || si?.region || amenityChips.length > 0 || si?.max_guests ? (
            <div className="mt-5 rounded-2xl border border-border/80 bg-card/40 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Your accommodation
              </p>
              {propertyAddress ? (
                <p className="mt-2 text-sm leading-relaxed text-foreground">{propertyAddress}</p>
              ) : null}
              {si?.region?.trim() ? (
                <p
                  className={
                    propertyAddress
                      ? "mt-1 text-xs text-muted-foreground"
                      : "mt-2 text-sm text-muted-foreground"
                  }
                >
                  {si.region.trim()}
                </p>
              ) : null}
              {si?.max_guests != null && si.max_guests > 0 ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Up to {si.max_guests} guest{si.max_guests === 1 ? "" : "s"}
                </p>
              ) : null}
              {amenityChips.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {amenityChips.slice(0, 12).map((a) => (
                    <span
                      key={a}
                      className="rounded-full border border-border/70 bg-background/80 px-2.5 py-1 text-xs text-foreground"
                    >
                      {a.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {stayChips.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {stayChips.map((c) => (
                <span
                  key={c.key}
                  className="inline-flex rounded-full border border-primary/25 bg-primary/5 px-3 py-1 text-xs font-medium text-primary"
                >
                  {c.label}
                </span>
              ))}
            </div>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/70 px-3 py-1.5 text-xs font-medium text-foreground shadow-sm backdrop-blur-sm">
              <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
              {recommendationCount === 0
                ? "No curated picks yet — your host may add more"
                : `${recommendationCount} ${recommendationCount === 1 ? "place suggested" : "places suggested"}`}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/70 px-3 py-1.5 text-xs font-medium text-foreground shadow-sm backdrop-blur-sm">
              <CalendarDays className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
              {hasItinerary ? "Itinerary from your host" : "No shared itinerary yet"}
            </span>
          </div>

          {hostOfferings?.recommendations?.local_tips &&
          hostOfferings.recommendations.local_tips.length > 0 ? (
            <div className="mt-5 rounded-2xl border border-border/80 bg-muted/30 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                From your host
              </p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-foreground/90">
                {hostOfferings.recommendations.local_tips.slice(0, 6).map((tip, i) => (
                  <li key={i}>{typeof tip === "string" ? tip : JSON.stringify(tip)}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {favoriteSpots.length > 0 ? (
            <div className="mt-5 rounded-2xl border border-border/80 bg-card/40 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Host&apos;s nearby favorites
              </p>
              <ul className="mt-3 space-y-3">
                {favoriteSpots.slice(0, 6).map((spot, i) => {
                  const label =
                    spot.name?.trim() ||
                    (spot.description?.trim()
                      ? spot.description.trim().slice(0, 80)
                      : "") ||
                    "Local spot";
                  const mapsUrl = mapsSearchUrlForFavoriteSpot(spot, city);
                  return (
                    <li
                      key={`${label}-${i}`}
                      className="rounded-xl border border-border/60 bg-background/60 p-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-foreground">{label}</p>
                          <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                            {spot.type ? (
                              <span className="rounded-md bg-muted px-1.5 py-0.5 capitalize">
                                {String(spot.type).replace(/_/g, " ")}
                              </span>
                            ) : null}
                            {typeof spot.distance_km === "number" ? (
                              <span>{spot.distance_km} km away</span>
                            ) : null}
                          </div>
                          {spot.description?.trim() ? (
                            <p className="mt-2 line-clamp-2 text-sm text-foreground/85">
                              {spot.description.trim()}
                            </p>
                          ) : null}
                          {spot.local_tip?.trim() ? (
                            <p className="mt-2 text-xs italic text-muted-foreground">
                              Tip: {spot.local_tip.trim()}
                            </p>
                          ) : null}
                        </div>
                        <a
                          href={mapsUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-primary/30 bg-primary/5 px-2.5 py-1.5 text-xs font-medium text-primary hover:bg-primary/10"
                        >
                          <MapPin className="h-3.5 w-3.5" aria-hidden />
                          Maps
                        </a>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          {(hi?.local_specialties?.length || hostOfferings?.recommendations?.expertise_areas?.length) ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {(hi?.local_specialties || []).slice(0, 8).map((s, i) => (
                <span
                  key={`s-${i}`}
                  className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-800 dark:text-emerald-200"
                >
                  {s}
                </span>
              ))}
              {(hostOfferings?.recommendations?.expertise_areas || [])
                .slice(0, 6)
                .map((s, i) => (
                  <span
                    key={`e-${i}`}
                    className="rounded-full bg-sky-500/10 px-2.5 py-1 text-xs font-medium text-sky-800 dark:text-sky-200"
                  >
                    {s}
                  </span>
                ))}
            </div>
          ) : null}

          {hostOfferings?.profile_extras?.location_story?.trim() ? (
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              {hostOfferings.profile_extras.location_story}
            </p>
          ) : null}

          {guestTestimonialBlocks.length > 0 ? (
            <div className="mt-5 rounded-2xl border border-primary/20 bg-primary/5 p-4">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Quote className="h-4 w-4 text-primary" aria-hidden />
                What guests say
              </p>
              <ul className="mt-3 space-y-4">
                {guestTestimonialBlocks.map((t, i) => (
                  <li key={i} className="border-l-2 border-primary/40 pl-3">
                    {typeof t.rating === "number" ? (
                      <p className="mb-1 text-xs text-amber-700 dark:text-amber-300">
                        <span aria-label={`Rating ${t.rating} out of 5`}>
                          {"★".repeat(Math.min(5, Math.max(0, Math.round(t.rating))))}
                        </span>
                      </p>
                    ) : null}
                    <blockquote className="text-sm italic leading-relaxed text-foreground/90">
                      &ldquo;{t.text}&rdquo;
                    </blockquote>
                    {t.author ? (
                      <p className="mt-1 text-xs font-medium text-muted-foreground">— {t.author}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Button type="button" className="w-full sm:w-auto" onClick={onContinue}>
              Discover places
            </Button>
            <Button
              type="button"
              variant="outline"
              className="w-full sm:w-auto"
              onClick={onViewItinerary}
            >
              View itinerary
            </Button>
            <Button
              type="button"
              variant="outline"
              className="w-full sm:w-auto"
              onClick={() => onNavigate("map")}
            >
              Open map
            </Button>
          </div>
        </div>
      </div>

      {primaryPref ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Your profile</CardTitle>
            <CardDescription>
              We use this to personalize Discover and Plan. Update anytime.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex flex-wrap gap-1.5">
              {(primaryPref.personal_interests?.length
                ? primaryPref.personal_interests
                : primaryPref.interests || []
              ).map((x) => (
                <span
                  key={x}
                  className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-foreground"
                >
                  {x}
                </span>
              ))}
            </div>
            <p className="text-muted-foreground">
              <span className="font-medium text-foreground">Age: </span>
              {primaryPref.age_category || primaryPref.age_range || "—"}
              {" · "}
              <span className="font-medium text-foreground">Mobility: </span>
              {primaryPref.mobility_notes?.trim()
                ? "see notes"
                : primaryPref.mobility_level || "—"}
              {" · "}
              <span className="font-medium text-foreground">Budget: </span>
              {primaryPref.budget_level || "—"}
            </p>
            {(primaryPref.dietary_needs?.length || 0) > 0 ? (
              <p className="text-muted-foreground">
                <span className="font-medium text-foreground">Diet: </span>
                {primaryPref.dietary_needs!.join(", ")}
              </p>
            ) : null}
            <Link
              href={`/guest/setup/${accessCode}`}
              className={cn(
                "inline-flex min-h-10 items-center justify-center rounded-2xl border-2 border-primary/35 bg-white/80 px-4 py-2 text-sm font-semibold text-primary transition-colors hover:bg-primary hover:text-primary-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 dark:bg-background/80"
              )}
            >
              Update preferences
            </Link>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card
          role="button"
          tabIndex={0}
          className="cursor-pointer transition-all hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
          onClick={() => onNavigate("recommendations")}
          onKeyDown={(e) => welcomeCardActivate(e, () => onNavigate("recommendations"))}
        >
          <CardContent className="p-6 text-center">
            <div className="mb-3 flex justify-center text-primary">
              <Landmark className="h-8 w-8" aria-hidden />
            </div>
            <h3 className="mb-2 font-semibold text-foreground">Authentic experiences</h3>
            <p className="text-sm text-muted-foreground">
              Hidden gems and local favorites curated by your Croatian host
            </p>
            <p className="mt-3 text-xs font-medium text-primary">Go to Discover →</p>
          </CardContent>
        </Card>
        <Card
          role="button"
          tabIndex={0}
          className="cursor-pointer transition-all hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
          onClick={() => onNavigate("itinerary")}
          onKeyDown={(e) => welcomeCardActivate(e, () => onNavigate("itinerary"))}
        >
          <CardContent className="p-6 text-center">
            <div className="mb-3 flex justify-center text-primary">
              <CalendarDays className="h-8 w-8" aria-hidden />
            </div>
            <h3 className="mb-2 font-semibold text-foreground">Personalized itinerary</h3>
            <p className="text-sm text-muted-foreground">
              Day plans tuned to your group&apos;s preferences
            </p>
            <p className="mt-3 text-xs font-medium text-primary">Go to Plan →</p>
          </CardContent>
        </Card>
        <Card
          role="button"
          tabIndex={0}
          className="cursor-pointer transition-all hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
          onClick={() => onNavigate("map")}
          onKeyDown={(e) => welcomeCardActivate(e, () => onNavigate("map"))}
        >
          <CardContent className="p-6 text-center">
            <div className="mb-3 flex justify-center text-primary">
              <Map className="h-8 w-8" aria-hidden />
            </div>
            <h3 className="mb-2 font-semibold text-foreground">Where things are</h3>
            <p className="text-sm text-muted-foreground">
              Map and nearby picks from your recommendations
            </p>
            <p className="mt-3 text-xs font-medium text-primary">Go to Map →</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const RecommendationsTab: React.FC<{
  guestGroup: GuestGroup;
  recommendations: Recommendation[];
  onNavigate: (tab: GuestTab) => void;
  onOpenDetail: (rec: Recommendation) => void;
  recFeedback: Record<string, 1 | 5>;
  onFeedback: (recId: string, rating: 1 | 5) => void | Promise<void>;
}> = ({ guestGroup, recommendations, onNavigate, onOpenDetail, recFeedback, onFeedback }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [busyFb, setBusyFb] = useState<string | null>(null);

  const categoryKeys = useMemo(() => {
    const set = new Set<string>();
    for (const r of recommendations) {
      const c = r.attraction?.category?.trim().toLowerCase();
      if (c) set.add(c);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [recommendations]);

  const filterChips = useMemo(
    () => ["all", ...categoryKeys] as string[],
    [categoryKeys]
  );

  const filteredRecommendations = useMemo(() => {
    if (selectedCategory === "all") return recommendations;
    return recommendations.filter(
      (r) => r.attraction?.category?.trim().toLowerCase() === selectedCategory
    );
  }, [recommendations, selectedCategory]);

  const groupLabel = guestGroup.group_name?.trim() || "your group";

  return (
    <div className="space-y-4">
      <div className="section-shell px-4 py-5 md:px-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Discover</h2>
            <p className="text-sm text-muted-foreground">
              {recommendations.length === 0
                ? `Your host has not shared curated places for ${groupLabel} yet.`
                : `${recommendations.length} ${recommendations.length === 1 ? "place" : "places"} suggested for ${groupLabel}.`}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => onNavigate("itinerary")}>
              Open Plan
            </Button>
            <Button variant="outline" onClick={() => onNavigate("map")}>
              Open Map
            </Button>
          </div>
        </div>
      </div>

      {recommendations.length > 0 && (
        <div className="surface-glass sticky top-0 z-20 rounded-2xl px-3 py-3">
          <p className="mb-2 px-1 text-xs font-medium text-muted-foreground">
            Filter by type
          </p>
          <div className="flex gap-2 overflow-x-auto pb-0.5">
            {filterChips.map((category) => (
              <button
                key={category}
                type="button"
                aria-pressed={selectedCategory === category}
                onClick={() => setSelectedCategory(category)}
                className={cn(
                  "shrink-0 rounded-full px-4 py-2 text-sm font-medium transition-colors",
                  selectedCategory === category
                    ? "bg-primary text-primary-foreground"
                    : "bg-white/70 text-foreground/80 hover:bg-primary/10"
                )}
              >
                {formatCategoryLabel(category)}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="py-2">
        {recommendations.length === 0 ? (
          <div className="section-shell py-12 text-center">
            <div className="mb-4 flex justify-center">
              <Search className="h-14 w-14 text-muted-foreground" aria-hidden />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-foreground">
              Nothing here yet
            </h3>
            <p className="mx-auto max-w-md text-muted-foreground">
              When your host adds suggestions, they will show up in Discover and on the map.
              You can still open <span className="font-medium text-foreground">Plan</span> if
              they shared an itinerary.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              <Button type="button" variant="outline" onClick={() => onNavigate("itinerary")}>
                Check Plan
              </Button>
              <Button type="button" variant="outline" onClick={() => onNavigate("map")}>
                Open Map
              </Button>
            </div>
          </div>
        ) : filteredRecommendations.length === 0 ? (
          <div className="section-shell py-12 text-center">
            <div className="mb-4 flex justify-center">
              <Search className="h-14 w-14 text-muted-foreground" aria-hidden />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-foreground">
              No places in this category
            </h3>
            <p className="mx-auto mb-6 max-w-md text-muted-foreground">
              Try another filter — all {recommendations.length}{" "}
              {recommendations.length === 1 ? "suggestion is" : "suggestions are"} in other
              types.
            </p>
            <Button type="button" onClick={() => setSelectedCategory("all")}>
              Show all places
            </Button>
          </div>
        ) : (
          <>
            <div className="md:hidden">
              <SnapScrollRow count={filteredRecommendations.length}>
                {filteredRecommendations.map((rec) => {
                  const season = seasonalPickBadge(rec.attraction);
                  const img = rec.attraction?.featured_image_url?.trim();
                  return (
                    <article
                      key={rec.id}
                      className="surface-card min-w-[84%] snap-center overflow-hidden transition-transform active:scale-[0.98]"
                    >
                      {img ? (
                        <button
                          type="button"
                          className="relative block aspect-video w-full overflow-hidden bg-muted text-left"
                          onClick={() => onOpenDetail(rec)}
                        >
                          <img
                            src={img}
                            alt=""
                            className="h-full w-full object-cover"
                            loading="lazy"
                          />
                        </button>
                      ) : null}
                      <div className="p-5">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                              {formatCategoryLabel(rec.attraction?.category || "experience")}
                            </p>
                            <h3 className="mt-1 text-lg font-semibold">
                              {rec.attraction?.name || "Place"}
                            </h3>
                          </div>
                          <span className="text-xl" aria-hidden>
                            {getCategoryIcon(rec.attraction?.category || "experience")}
                          </span>
                        </div>
                        {season ? (
                          <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:text-emerald-200">
                            <Leaf className="h-3.5 w-3.5" aria-hidden />
                            {season}
                          </p>
                        ) : null}
                        <p className="mt-3 text-sm text-muted-foreground">
                          {rec.attraction?.description?.trim() ||
                            "Your host highlighted this spot for your stay."}
                        </p>
                        <div className="mt-4 rounded-2xl bg-primary/10 p-3 text-sm">
                          <p className="font-medium text-primary">Why it fits you</p>
                          <p className="mt-1 text-foreground/80">{rec.reason}</p>
                        </div>
                        {rec.personalization_factors &&
                        rec.personalization_factors.length > 0 ? (
                          <div className="mt-3 flex flex-wrap gap-1">
                            {rec.personalization_factors.slice(0, 5).map((factor, idx) => (
                              <span
                                key={idx}
                                className="rounded-full bg-accent/15 px-2 py-1 text-xs text-foreground/80"
                              >
                                {factor}
                              </span>
                            ))}
                          </div>
                        ) : null}
                        {rec.attraction?.location ? (
                          <p className="mt-3 flex items-center gap-1 text-sm text-muted-foreground">
                            <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden />
                            {rec.attraction.location}
                          </p>
                        ) : null}
                        <div className="mt-4 flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            type="button"
                            variant="outline"
                            onClick={() => onOpenDetail(rec)}
                          >
                            Details
                          </Button>
                          <Button
                            size="sm"
                            type="button"
                            variant="outline"
                            onClick={() => onNavigate("map")}
                          >
                            On map
                          </Button>
                          <Button
                            size="sm"
                            type="button"
                            disabled={!mapsUrlForAttraction(rec.attraction)}
                            onClick={() => openAttractionInMaps(rec.attraction)}
                          >
                            Directions
                          </Button>
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border/60 pt-3">
                          <span className="text-xs text-muted-foreground">Helpful?</span>
                          <Button
                            size="sm"
                            type="button"
                            variant={recFeedback[rec.id] === 5 ? "primary" : "outline"}
                            disabled={busyFb === rec.id}
                            className="gap-1"
                            onClick={() => {
                              setBusyFb(rec.id);
                              void Promise.resolve(onFeedback(rec.id, 5)).finally(() =>
                                setBusyFb(null)
                              );
                            }}
                          >
                            <ThumbsUp className="h-4 w-4" aria-hidden />
                            Yes
                          </Button>
                          <Button
                            size="sm"
                            type="button"
                            variant={recFeedback[rec.id] === 1 ? "primary" : "outline"}
                            disabled={busyFb === rec.id}
                            className="gap-1"
                            onClick={() => {
                              setBusyFb(rec.id);
                              void Promise.resolve(onFeedback(rec.id, 1)).finally(() =>
                                setBusyFb(null)
                              );
                            }}
                          >
                            <ThumbsDown className="h-4 w-4" aria-hidden />
                            No
                          </Button>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </SnapScrollRow>
            </div>

            <div className="hidden md:block">
              <BentoGrid
                items={filteredRecommendations.map((rec) => {
                  const season = seasonalPickBadge(rec.attraction);
                  const img = rec.attraction?.featured_image_url?.trim();
                  return {
                    title: rec.attraction?.name || "Place",
                    description:
                      rec.attraction?.description?.trim() ||
                      "Your host highlighted this spot for your stay.",
                    headerImage: img || undefined,
                    icon: getCategoryIcon(rec.attraction?.category || "experience"),
                    category: rec.attraction?.category,
                    cost: rec.attraction?.cost_estimate,
                    authenticity: rec.attraction?.authenticity_level,
                    bestTime: season || undefined,
                    className: "cursor-pointer",
                    onClick: () => onOpenDetail(rec),
                    content: (
                      <div className="space-y-4">
                        {season ? (
                          <p className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-1 text-xs font-medium text-emerald-800 dark:text-emerald-200">
                            <Leaf className="h-3.5 w-3.5" aria-hidden />
                            {season}
                          </p>
                        ) : null}
                        {rec.attraction?.location ? (
                          <span className="flex items-center gap-1 text-sm text-muted-foreground">
                            <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden />
                            {rec.attraction.location}
                          </span>
                        ) : null}
                        <div className="rounded-2xl bg-primary/10 p-3">
                          <p className="text-sm font-medium text-primary">Why it fits you</p>
                          <p className="text-sm text-foreground/80">{rec.reason}</p>
                        </div>
                        {rec.personalization_factors &&
                        rec.personalization_factors.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {rec.personalization_factors.slice(0, 5).map((factor, idx) => (
                              <span
                                key={idx}
                                className="rounded-full bg-accent/15 px-2 py-1 text-xs text-foreground/80"
                              >
                                {factor}
                              </span>
                            ))}
                          </div>
                        ) : null}
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            type="button"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              onNavigate("map");
                            }}
                          >
                            On map
                          </Button>
                          <Button
                            size="sm"
                            type="button"
                            disabled={!mapsUrlForAttraction(rec.attraction)}
                            onClick={(e) => {
                              e.stopPropagation();
                              openAttractionInMaps(rec.attraction);
                            }}
                          >
                            Directions
                          </Button>
                        </div>
                        <div
                          className="flex flex-wrap items-center gap-2 border-t border-gray-200 pt-3"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <span className="text-xs text-gray-500">Helpful?</span>
                          <Button
                            size="sm"
                            type="button"
                            variant={recFeedback[rec.id] === 5 ? "primary" : "outline"}
                            disabled={busyFb === rec.id}
                            className="gap-1"
                            onClick={() => {
                              setBusyFb(rec.id);
                              void Promise.resolve(onFeedback(rec.id, 5)).finally(() =>
                                setBusyFb(null)
                              );
                            }}
                          >
                            <ThumbsUp className="h-4 w-4" aria-hidden />
                            Yes
                          </Button>
                          <Button
                            size="sm"
                            type="button"
                            variant={recFeedback[rec.id] === 1 ? "primary" : "outline"}
                            disabled={busyFb === rec.id}
                            className="gap-1"
                            onClick={() => {
                              setBusyFb(rec.id);
                              void Promise.resolve(onFeedback(rec.id, 1)).finally(() =>
                                setBusyFb(null)
                              );
                            }}
                          >
                            <ThumbsDown className="h-4 w-4" aria-hidden />
                            No
                          </Button>
                        </div>
                      </div>
                    ),
                  };
                })}
                className="grid-cols-1 md:grid-cols-2 xl:grid-cols-3"
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
};

function openItineraryActivityMaps(activity: ItineraryActivity) {
  const url = mapsUrlForItineraryActivity(activity);
  if (url) window.open(url, "_blank", "noopener,noreferrer");
}

const ItineraryTab: React.FC<{
  guestGroup: GuestGroup;
  itineraries: Itinerary[];
  onNavigate: (tab: GuestTab) => void;
  accessCode: string;
}> = ({ guestGroup, itineraries, onNavigate, accessCode }) => {
  const groupLabel = guestGroup.group_name?.trim() || "your group";
  const [busyVote, setBusyVote] = useState<string | null>(null);
  const [busyCheck, setBusyCheck] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <div className="section-shell px-4 py-5 md:px-6">
        <h2 className="text-2xl font-semibold">Plan</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {itineraries.length > 0
            ? `Shared schedule for ${groupLabel}. Times, tips, and travel hints come from your host.`
            : `When your host publishes an itinerary for ${groupLabel}, it will show up here.`}
        </p>
      </div>

      <div className="py-2">
        {itineraries.length > 0 ? (
          <div className="space-y-8">
            {itineraries.map((itinerary) => {
              const days = itinerary.day_plans ?? [];
              return (
                <Card key={itinerary.id} className="overflow-hidden">
                  <CardHeader className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-950/40 dark:to-blue-950/40">
                    <CardTitle>{itinerary.title || "Your trip plan"}</CardTitle>
                    <CardDescription>
                      {itinerary.description?.trim() ||
                        "Overview from your host — details may be updated over time."}
                    </CardDescription>
                    {(itinerary.start_date || itinerary.end_date) && (
                      <p className="pt-1 text-xs text-muted-foreground">
                        {itinerary.start_date && itinerary.end_date
                          ? `${itinerary.start_date} → ${itinerary.end_date}`
                          : itinerary.start_date || itinerary.end_date}
                      </p>
                    )}
                  </CardHeader>
                  <CardContent className="p-6">
                    {days.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        Your host has started an itinerary but hasn&apos;t added days yet.
                        Check back later or browse{" "}
                        <button
                          type="button"
                          className="font-medium text-primary underline-offset-2 hover:underline"
                          onClick={() => onNavigate("recommendations")}
                        >
                          Discover
                        </button>{" "}
                        for ideas.
                      </p>
                    ) : (
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {days.map((dayPlan) => (
                          <div
                            key={dayPlan.id}
                            className="rounded-xl border border-border/80 bg-card/50 p-4"
                          >
                            <h4 className="font-semibold text-foreground">
                              Day {dayPlan.day_number}
                              {dayPlan.theme ? `: ${dayPlan.theme}` : ""}
                            </h4>
                            {dayPlan.description?.trim() ? (
                              <p className="mt-2 text-sm text-muted-foreground">
                                {dayPlan.description}
                              </p>
                            ) : null}
                            {dayPlan.host_tips?.trim() ? (
                              <div className="mt-2 rounded-lg bg-primary/10 p-2 text-sm text-foreground/90">
                                <span className="font-medium text-primary">Host tip for the day</span>
                                <p className="mt-1">{dayPlan.host_tips}</p>
                              </div>
                            ) : null}
                            {(dayPlan.total_distance != null ||
                              dayPlan.total_travel_time != null) && (
                              <p className="mt-2 text-xs text-muted-foreground">
                                {dayPlan.total_distance != null
                                  ? `~${dayPlan.total_distance} km`
                                  : ""}
                                {dayPlan.total_distance != null &&
                                dayPlan.total_travel_time != null
                                  ? " · "
                                  : ""}
                                {dayPlan.total_travel_time != null
                                  ? `~${dayPlan.total_travel_time} min travel`
                                  : ""}
                              </p>
                            )}
                            <div className="mt-3 space-y-3">
                              {(dayPlan.activities ?? []).length === 0 ? (
                                <p className="text-sm text-muted-foreground">
                                  No activities listed for this day yet.
                                </p>
                              ) : (
                                (dayPlan.activities ?? []).map((activity, actIdx) => {
                                  const travelMin = activity.travel_time_minutes ?? 0;
                                  const travelKm = activity.travel_distance_km ?? 0;
                                  return (
                                  <div
                                    key={activity.id}
                                    className="rounded-lg border border-border/70 bg-background/80 p-3 text-sm"
                                  >
                                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                                      <span className="font-semibold text-foreground">
                                        {activityTimeLabel(activity)}
                                      </span>
                                      <span className="text-muted-foreground">
                                        {activityDisplayTitle(activity)}
                                      </span>
                                    </div>
                                    {activity.description?.trim() ? (
                                      <p className="mt-2 text-muted-foreground">
                                        {activity.description}
                                      </p>
                                    ) : null}
                                    {activity.host_tip?.trim() ? (
                                      <div className="mt-2 rounded-md bg-amber-500/10 p-2 text-xs text-foreground/90">
                                        <span className="font-medium text-amber-800 dark:text-amber-200">
                                          Host tip
                                        </span>
                                        <p className="mt-0.5">{activity.host_tip}</p>
                                      </div>
                                    ) : null}
                                    {actIdx > 0 && (travelMin > 0 || travelKm > 0) ? (
                                      <p className="mt-2 text-xs text-muted-foreground">
                                        From previous:{" "}
                                        {travelMin ? `${travelMin} min` : ""}
                                        {travelMin && travelKm ? " · " : ""}
                                        {travelKm ? `${travelKm} km` : ""}
                                      </p>
                                    ) : null}
                                    {activity.estimated_duration ? (
                                      <p className="mt-1 text-xs text-muted-foreground">
                                        ~{activity.estimated_duration} min at place
                                      </p>
                                    ) : null}
                                    {activity.cost_per_person != null ? (
                                      <p className="mt-1 text-xs font-medium text-foreground">
                                        ~{activity.cost_per_person}€ / person
                                      </p>
                                    ) : null}
                                    {(activity.location_name || activity.address) && (
                                      <p className="mt-2 flex items-start gap-1 text-xs text-muted-foreground">
                                        <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                                        <span>
                                          {[activity.location_name, activity.address]
                                            .filter(Boolean)
                                            .join(" · ")}
                                        </span>
                                      </p>
                                    )}
                                    <div className="mt-3 flex flex-wrap gap-2">
                                      <Button
                                        type="button"
                                        size="sm"
                                        variant="outline"
                                        disabled={!mapsUrlForItineraryActivity(activity)}
                                        onClick={() => openItineraryActivityMaps(activity)}
                                      >
                                        Directions
                                      </Button>
                                    </div>
                                    <div className="mt-2 flex flex-wrap gap-1 border-t border-border/50 pt-2">
                                      <span className="w-full text-xs text-muted-foreground">
                                        Vote on this stop
                                      </span>
                                      {(["yes", "maybe", "no"] as const).map((v) => (
                                        <Button
                                          key={v}
                                          type="button"
                                          size="sm"
                                          variant="outline"
                                          className="h-8 capitalize"
                                          disabled={busyVote === activity.id}
                                          onClick={() => {
                                            setBusyVote(activity.id);
                                            void itinerariesApi
                                              .voteActivity(accessCode, activity.id, {
                                                vote: v,
                                              })
                                              .finally(() => setBusyVote(null));
                                          }}
                                        >
                                          {v}
                                        </Button>
                                      ))}
                                      <Button
                                        type="button"
                                        size="sm"
                                        variant="secondary"
                                        className="h-8 gap-1"
                                        disabled={busyCheck === activity.id}
                                        onClick={() => {
                                          setBusyCheck(activity.id);
                                          void itinerariesApi
                                            .checkInActivity(accessCode, activity.id)
                                            .finally(() => setBusyCheck(null));
                                        }}
                                      >
                                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                                        Check in
                                      </Button>
                                    </div>
                                  </div>
                                  );
                                })
                              )}
                            </div>
                            <div className="mt-3 text-xs text-muted-foreground">
                              {dayPlan.estimated_cost != null
                                ? `Est. day cost: ${dayPlan.estimated_cost}€`
                                : "Est. cost: —"}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                  <CardFooter className="flex flex-col gap-3 border-t bg-muted/20 sm:flex-row sm:flex-wrap">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => onNavigate("recommendations")}
                    >
                      Browse Discover
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => onNavigate("map")}
                    >
                      Open Map
                    </Button>
                  </CardFooter>
                </Card>
              );
            })}
          </div>
        ) : (
          <div className="section-shell py-12 text-center">
            <div className="mb-4 flex justify-center">
              <CalendarDays className="h-14 w-14 text-muted-foreground" aria-hidden />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-foreground">No itinerary yet</h3>
            <p className="mx-auto mb-6 max-w-md text-muted-foreground">
              Your host hasn&apos;t shared a day-by-day plan. You can still explore suggested
              places in Discover and on the map.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              <Button type="button" onClick={() => onNavigate("recommendations")}>
                Go to Discover
              </Button>
              <Button type="button" variant="outline" onClick={() => onNavigate("map")}>
                Open Map
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const MapTab: React.FC<{
  guestGroup: GuestGroup;
  recommendations: Recommendation[];
  hostOfferings: GuestHostOfferingsPayload | null;
  onNavigate: (tab: GuestTab) => void;
  onOpenRecommendationDetail: (rec: Recommendation) => void;
}> = ({
  guestGroup,
  recommendations,
  hostOfferings,
  onNavigate,
  onOpenRecommendationDetail,
}) => {
  const groupLabel = guestGroup.group_name?.trim() || "your group";

  const mapMarkers = useMemo(() => {
    const out: Array<{
      id: string;
      lat: number;
      lng: number;
      title: string;
      subtitle?: string;
      category?: string;
      attraction?: Attraction;
    }> = [];
    for (const rec of recommendations) {
      const a = rec.attraction;
      if (!a) continue;
      let lat: number | undefined;
      let lng: number | undefined;
      if (typeof a.latitude === "number" && typeof a.longitude === "number") {
        lat = a.latitude;
        lng = a.longitude;
      } else if (Array.isArray(a.coordinates) && a.coordinates.length >= 2) {
        const [x, y] = a.coordinates;
        if (typeof x === "number" && typeof y === "number") {
          lat = x;
          lng = y;
        }
      }
      if (lat == null || lng == null) continue;
      out.push({
        id: rec.id,
        lat,
        lng,
        title: a.name || "Place",
        subtitle: a.location || a.city || undefined,
        category: a.category,
        attraction: a,
      });
    }
    return out;
  }, [recommendations]);

  const hostMarker = useMemo(() => {
    const c = hostOfferings?.location_info?.coordinates;
    if (c?.lat == null || c?.lng == null) return null;
    return {
      lat: c.lat,
      lng: c.lng,
      title: hostOfferings?.host_info?.name
        ? `${hostOfferings.host_info.name}'s place`
        : "Your stay",
    };
  }, [hostOfferings]);

  const listSpots = recommendations;

  return (
    <div className="space-y-4">
      <div className="section-shell px-4 py-5 md:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Map</h2>
            <p className="text-sm text-muted-foreground">
              {recommendations.length === 0
                ? `No pinned places yet for ${groupLabel}.`
                : mapMarkers.length === 0
                  ? `${recommendations.length} suggestion${recommendations.length === 1 ? "" : "s"} — add coordinates on attractions to see pins.`
                  : `${mapMarkers.length} on map of ${recommendations.length} suggested ${recommendations.length === 1 ? "spot" : "spots"}.`}
            </p>
          </div>
          <Button variant="outline" onClick={() => onNavigate("recommendations")}>
            Back to Discover
          </Button>
        </div>
      </div>

      {recommendations.length === 0 ? (
        <div className="section-shell py-10 text-center">
          <Map className="mx-auto mb-3 h-12 w-12 text-muted-foreground" aria-hidden />
          <p className="text-sm text-muted-foreground">
            Once your host adds suggestions, they will appear here with quick links to maps.
          </p>
          <Button type="button" className="mt-4" onClick={() => onNavigate("recommendations")}>
            Go to Discover
          </Button>
        </div>
      ) : (
        <>
          <div className="relative overflow-hidden rounded-3xl border border-border/70 bg-muted/20 p-2 md:p-3">
            <div className="h-[42vh] overflow-hidden rounded-2xl border border-border/50 md:h-[48vh]">
              {mapMarkers.length > 0 ? (
                <GuestMap
                  markers={mapMarkers}
                  hostMarker={hostMarker}
                  onOpenDetails={(id) => {
                    const rec = recommendations.find((r) => r.id === id);
                    if (rec) onOpenRecommendationDetail(rec);
                  }}
                  className="z-0 rounded-2xl"
                />
              ) : (
                <div className="flex h-full items-center justify-center bg-gradient-to-br from-cyan-100/50 via-sky-100/40 to-orange-100/40 px-4 dark:from-cyan-950/30 dark:via-sky-950/20 dark:to-orange-950/20">
                  <div className="max-w-md text-center">
                    <Map className="mx-auto mb-3 h-12 w-12 text-muted-foreground" aria-hidden />
                    <h3 className="text-lg font-semibold text-foreground">No map pins yet</h3>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Your host&apos;s places need latitude/longitude to appear on the map. Use the
                      list below for directions.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="surface-glass relative z-20 mt-3 max-h-[40vh] overflow-y-auto p-3 md:hidden">
              <p className="mb-2 text-sm font-semibold text-foreground">Suggested spots</p>
              <SnapScrollRow count={listSpots.length}>
                {listSpots.map((rec) => (
                  <div
                    key={rec.id}
                    className="surface-card flex min-w-[220px] flex-col gap-2 px-3 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {rec.attraction?.name || "Place"}
                      </p>
                      {rec.attraction?.location ? (
                        <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                          <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden />
                          {rec.attraction.location}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        type="button"
                        variant="outline"
                        className="shrink-0"
                        onClick={() => onOpenRecommendationDetail(rec)}
                      >
                        Details
                      </Button>
                      <Button
                        size="sm"
                        type="button"
                        variant="outline"
                        className="shrink-0"
                        disabled={!mapsUrlForAttraction(rec.attraction)}
                        onClick={() => openAttractionInMaps(rec.attraction)}
                      >
                        Directions
                      </Button>
                    </div>
                  </div>
                ))}
              </SnapScrollRow>
            </div>
          </div>

          <div className="hidden py-2 md:block">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {listSpots.map((rec) => (
                <Card key={rec.id} className="transition-shadow hover:shadow-md">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="text-2xl" aria-hidden>
                        {getCategoryIcon(rec.attraction?.category || "experience")}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h4 className="font-semibold text-foreground">
                          {rec.attraction?.name || "Place"}
                        </h4>
                        {rec.attraction?.location ? (
                          <p className="mb-3 mt-1 flex items-center gap-1 text-sm text-muted-foreground">
                            <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden />
                            {rec.attraction.location}
                          </p>
                        ) : (
                          <div className="mb-3" />
                        )}
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            type="button"
                            variant="outline"
                            onClick={() => onOpenRecommendationDetail(rec)}
                          >
                            Details
                          </Button>
                          <Button
                            size="sm"
                            type="button"
                            variant="outline"
                            disabled={!mapsUrlForAttraction(rec.attraction)}
                            onClick={() => openAttractionInMaps(rec.attraction)}
                          >
                            Open in Maps
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const GuestMessageFab: React.FC<{
  accessCode: string;
  hostOfferings: GuestHostOfferingsPayload | null;
  activeTab: GuestTab;
}> = ({ accessCode, hostOfferings, activeTab }) => {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState<string | null>(null);

  if (activeTab === "maintenance") return null;

  const responseHint =
    hostOfferings?.contact?.response_time || "Usually within 2 hours";

  const send = async () => {
    if (!text.trim()) return;
    setBusy(true);
    setReply(null);
    const r = await guestGroupsApi.sendHostMessage(accessCode, {
      message: text.trim(),
      type: "general",
    });
    setBusy(false);
    if (!r.success) {
      setReply(r.error || "Could not send. Try again later.");
      return;
    }
    setReply(r.data?.message || "Sent.");
    setText("");
  };

  return (
    <>
      <button
        type="button"
        className="fixed bottom-24 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105 md:bottom-8"
        onClick={() => {
          setOpen(true);
          setReply(null);
        }}
        aria-label="Message host"
      >
        <MessageCircle className="h-7 w-7" aria-hidden />
      </button>
      {open ? (
        <div className="fixed inset-0 z-[110] flex items-end justify-center sm:items-center sm:p-4">
          <button
            type="button"
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            aria-label="Close"
            onClick={() => setOpen(false)}
          />
          <div className="relative z-[111] w-full max-w-md rounded-t-3xl border border-border bg-background p-5 shadow-2xl sm:rounded-3xl">
            <h3 className="text-lg font-semibold text-foreground">Message your host</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Quick note or question. {responseHint}.
            </p>
            <textarea
              className="mt-3 min-h-[100px] w-full rounded-xl border border-input bg-background px-3 py-2 text-sm"
              placeholder="e.g. Could we get an extra towel?"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            {reply ? (
              <p className="mt-2 rounded-lg border border-border bg-muted/50 px-3 py-2 text-sm text-foreground">
                {reply}
              </p>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button type="button" disabled={busy || !text.trim()} onClick={() => void send()}>
                {busy ? "Sending…" : "Send"}
              </Button>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};

const MAINTENANCE_CATEGORY_LABELS: Record<string, string> = {
  plumbing: "Plumbing & water",
  electrical: "Electrical",
  hvac: "Heating / cooling",
  appliances: "Appliances",
  connectivity: "WiFi / TV / tech",
  cleaning: "Cleaning",
  other: "Other",
};

const GuestMaintenanceReportPanel: React.FC<{ accessCode: string }> = ({ accessCode }) => {
  const [category, setCategory] = useState("plumbing");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [msgTone, setMsgTone] = useState<"neutral" | "error" | "success">("neutral");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!title.trim()) {
      setMsgTone("error");
      setMsg("Add a short title so your host knows what to look for.");
      return;
    }
    setBusy(true);
    setMsg(null);
    setMsgTone("neutral");
    const r = await guestMaintenanceApi.report({
      access_code: accessCode,
      category,
      title: title.trim(),
      description: description.trim() || undefined,
    });
    setBusy(false);
    if (!r.success) {
      setMsgTone("error");
      setMsg(r.error || "Could not send report. Try again or contact your host directly.");
      return;
    }
    setMsgTone("success");
    setMsg("Sent. Your host will see this in their dashboard.");
    setTitle("");
    setDescription("");
  };

  return (
    <div className="space-y-4">
      <div className="section-shell px-4 py-5 md:px-6">
        <h2 className="text-2xl font-semibold">Report an issue</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          For problems at the property (leaks, power, AC, appliances). This is not for tour
          bookings — use Discover and Plan for activities.
        </p>
      </div>

      <div className="mx-auto max-w-lg px-1 pb-8 md:px-0">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5" aria-hidden />
              Message to your host
            </CardTitle>
            <CardDescription>
              One report per issue is enough. Add photos in a follow-up message to your host if
              needed.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {msg ? (
              <p
                className={cn(
                  "rounded-lg border px-3 py-2 text-sm",
                  msgTone === "success" &&
                    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100",
                  msgTone === "error" &&
                    "border-destructive/30 bg-destructive/10 text-destructive dark:text-red-200",
                  msgTone === "neutral" && "border-border bg-muted/40 text-muted-foreground"
                )}
                role={msgTone === "error" ? "alert" : undefined}
              >
                {msg}
              </p>
            ) : null}
            <div>
              <label className="text-xs font-medium text-muted-foreground" htmlFor="gm-cat">
                Category
              </label>
              <select
                id="gm-cat"
                className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {Object.entries(MAINTENANCE_CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground" htmlFor="gm-title">
                Short title
              </label>
              <input
                id="gm-title"
                className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Hot water cuts out after 5 minutes"
                autoComplete="off"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground" htmlFor="gm-desc">
                Details (optional)
              </label>
              <textarea
                id="gm-desc"
                className="mt-1 min-h-[100px] w-full rounded-md border border-input bg-background px-2 py-2 text-sm"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Room, when it happens, what you already tried…"
              />
            </div>
            <Button type="button" disabled={busy} onClick={submit}>
              {busy ? "Sending…" : "Send to host"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

function getCategoryIcon(category: string): React.ReactNode {
  const icons: Record<string, React.ReactNode> = {
    cultural: <Landmark className="h-5 w-5" />,
    nature: <Trees className="h-5 w-5" />,
    food: <UtensilsCrossed className="h-5 w-5" />,
    activities: <Compass className="h-5 w-5" />,
    beaches: <Waves className="h-5 w-5" />,
    historical: <Landmark className="h-5 w-5" />,
    entertainment: <PartyPopper className="h-5 w-5" />,
    shopping: <ShoppingBag className="h-5 w-5" />,
  };
  return icons[category] || <MapPin className="h-5 w-5" />;
}
