"use client";

import React from "react";
import { CalendarDays, ExternalLink, Lightbulb, MapPin, PartyPopper, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { GuestEventRecommendation, GuestHostOfferingsPayload } from "@/lib/api";

export interface GuestSeasonalEvent {
  id: string;
  name: string;
  description: string;
  event_type: string;
  city: string;
  location?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  host_recommendation?: string | null;
}

function looksLikeEventCity(name: string): boolean {
  const t = name.trim();
  if (!t || t.length < 2) return false;
  return !/\s\d{1,4}[a-zA-Z]?$/.test(t);
}

export function resolveGuestCity(
  hostOfferings: GuestHostOfferingsPayload | null,
  fallback = "Lovran"
): string {
  const candidates = [
    hostOfferings?.host_info?.broader_city,
    hostOfferings?.location_info?.city,
    hostOfferings?.host_info?.city,
    hostOfferings?.stay_info?.city,
  ]
    .map((c) => c?.trim())
    .filter((c): c is string => Boolean(c));

  const suitable = candidates.find(looksLikeEventCity);
  return suitable || candidates[0] || fallback;
}

function formatEventDate(start?: string | null, end?: string | null) {
  if (!start) return null;
  try {
    const s = new Date(start);
    const e = end ? new Date(end) : null;
    const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
    if (e && !Number.isNaN(e.getTime())) {
      return `${s.toLocaleDateString(undefined, opts)} – ${e.toLocaleDateString(undefined, opts)}`;
    }
    return s.toLocaleDateString(undefined, opts);
  } catch {
    return null;
  }
}

function savedEventScheduleLabel(saved?: {
  itinerary_activity_start_time?: string;
}): string | null {
  if (!saved?.itinerary_activity_start_time) return null;
  try {
    const start = new Date(saved.itinerary_activity_start_time);
    if (Number.isNaN(start.getTime())) return null;
    const date = start.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
    const time = start.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
    return `${date} at ${time}`;
  } catch {
    return null;
  }
}

function priorityStyles(priority: string) {
  if (priority === "high") {
    return "border-violet-400/50 bg-violet-500/10 text-violet-900 dark:text-violet-100";
  }
  if (priority === "medium") {
    return "border-sky-400/40 bg-sky-500/10 text-sky-900 dark:text-sky-100";
  }
  return "border-border/70 bg-muted/40 text-muted-foreground";
}

export const GuestEventRecommendationCard: React.FC<{
  rec: GuestEventRecommendation;
  className?: string;
  saved?: boolean;
  savedDetails?: {
    host_status?: string;
    host_note?: string;
    host_action_at?: string;
    planned_at?: string;
    itinerary_activity_id?: string;
    itinerary_activity_start_time?: string;
  };
  onToggleSave?: (rec: GuestEventRecommendation) => void;
}> = ({ rec, className, saved, savedDetails, onToggleSave }) => {
  const scheduleLabel = savedEventScheduleLabel(savedDetails);
  const dates = formatEventDate(rec.start_date, rec.end_date);
  const meta = [
    rec.cities?.length ? rec.cities.join(", ") : null,
    dates,
    rec.distance_km != null ? `~${rec.distance_km} km` : null,
    rec.source === "seasonal" ? "Host pick" : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <article
      className={cn(
        "rounded-xl border border-border/70 bg-card/80 p-4 shadow-sm transition-shadow hover:shadow-md",
        className
      )}
      data-testid="guest-event-recommendation"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
            priorityStyles(rec.priority)
          )}
        >
          {rec.priority} match
        </span>
        {rec.event_type ? (
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground">
            {rec.event_type.replace(/_/g, " ")}
          </span>
        ) : null}
        {meta ? <span className="text-xs text-muted-foreground">{meta}</span> : null}
        {savedDetails?.itinerary_activity_id ? (
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-900 dark:text-emerald-100">
            In itinerary
          </span>
        ) : savedDetails?.host_status === "planned" ? (
          <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-900 dark:text-emerald-100">
            Host planned
          </span>
        ) : null}
      </div>

      <h3 className="mt-2 font-semibold text-foreground">
        {rec.url ? (
          <a
            href={rec.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 hover:text-primary hover:underline"
          >
            {rec.title}
            <ExternalLink className="h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden />
          </a>
        ) : (
          rec.title
        )}
      </h3>

      <p className="mt-1 line-clamp-3 text-sm leading-relaxed text-muted-foreground">
        {rec.description}
      </p>

      <p className="mt-2 flex items-start gap-1.5 text-xs text-foreground/85">
        <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
        {rec.why_recommended}
      </p>

      <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-amber-500/10 px-2.5 py-2 text-xs text-amber-950 dark:text-amber-100">
        <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        <span>{rec.plan_hint}</span>
      </p>

      {scheduleLabel ? (
        <p className="mt-2 rounded-lg bg-emerald-500/10 px-2.5 py-2 text-xs text-emerald-950 dark:text-emerald-100">
          Scheduled {scheduleLabel}
        </p>
      ) : savedDetails?.host_status === "planned" ? (
        <p className="mt-2 rounded-lg bg-emerald-500/10 px-2.5 py-2 text-xs text-emerald-950 dark:text-emerald-100">
          Your host marked this as planned
          {savedDetails.host_action_at
            ? ` on ${new Date(savedDetails.host_action_at).toLocaleDateString()}`
            : ""}
          .
        </p>
      ) : null}

      {onToggleSave ? (
        <Button
          type="button"
          size="sm"
          variant={saved ? "secondary" : "outline"}
          className="mt-3"
          onClick={() => onToggleSave(rec)}
        >
          {saved ? "Saved to plan" : "Save to plan"}
        </Button>
      ) : null}
    </article>
  );
};

export const GuestEventsPreview: React.FC<{
  recommendations: GuestEventRecommendation[];
  savedOnlyRecommendations?: GuestEventRecommendation[];
  city: string;
  onViewAll: () => void;
}> = ({ recommendations, savedOnlyRecommendations = [], city, onViewAll }) => {
  const seen = new Set<string>();
  const previewItems = [...savedOnlyRecommendations, ...recommendations]
    .filter((r) => (seen.has(r.id) ? false : (seen.add(r.id), true)))
    .slice(0, 3);
  if (previewItems.length === 0) return null;
  const savedOnlyIds = new Set(savedOnlyRecommendations.map((r) => r.id));
  const headerLabel =
    recommendations.length === 0
      ? "Saved event ideas for your stay"
      : `Picked for your stay near ${city}`;
  return (
    <div
      className="mt-5 rounded-2xl border border-violet-200/80 bg-violet-50/50 p-4 dark:border-violet-900/40 dark:bg-violet-950/20"
      data-testid="guest-events-preview"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-violet-800 dark:text-violet-200">
          <PartyPopper className="h-4 w-4" aria-hidden />
          {headerLabel}
        </p>
        <Button type="button" size="sm" variant="outline" onClick={onViewAll}>
          All events
        </Button>
      </div>
      <ul className="mt-3 space-y-2">
        {previewItems.map((rec) => (
          <li
            key={`preview-${rec.id}`}
            className="rounded-lg bg-background/80 px-3 py-2"
            data-testid={
              savedOnlyIds.has(rec.id)
                ? "guest-events-preview-saved"
                : "guest-events-preview-live"
            }
          >
            <p className="font-medium text-sm text-foreground">{rec.title}</p>
            <p className="line-clamp-1 text-xs text-muted-foreground">{rec.why_recommended}</p>
          </li>
        ))}
      </ul>
    </div>
  );
};

export const GuestEventsTab: React.FC<{
  city: string;
  recommendations: GuestEventRecommendation[];
  savedOnlyRecommendations?: GuestEventRecommendation[];
  savedEventIds: string[];
  savedEventDetails: Record<
    string,
    {
      host_status?: string;
      host_note?: string;
      host_action_at?: string;
      planned_at?: string;
      itinerary_activity_id?: string;
      itinerary_activity_start_time?: string;
    }
  >;
  onToggleSaveEvent: (rec: GuestEventRecommendation) => void;
  onNavigateDiscover: () => void;
  onNavigatePlan?: () => void;
}> = ({
  city,
  recommendations,
  savedOnlyRecommendations = [],
  savedEventIds,
  savedEventDetails,
  onToggleSaveEvent,
  onNavigateDiscover,
  onNavigatePlan,
}) => {
  const hasAny = recommendations.length > 0 || savedOnlyRecommendations.length > 0;
  const savedSet = new Set(savedEventIds);
  const hostPicks = recommendations.filter((r) => r.source === "seasonal");
  const feedPicks = recommendations.filter((r) => r.source === "feed");

  return (
    <div className="space-y-4" data-testid="guest-events-tab">
      <div className="section-shell px-4 py-5 md:px-6">
        <h2 className="text-2xl font-semibold text-foreground">Events for your stay</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Personalized festivals and happenings around {city} — matched to your interests, dates,
          and distance from your accommodation.
        </p>
      </div>

      {savedOnlyRecommendations.length > 0 ? (
        <Card
          className="mx-1 border-violet-200/70 bg-violet-50/40 md:mx-0 dark:border-violet-900/40 dark:bg-violet-950/15"
          data-testid="guest-events-saved-section"
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <PartyPopper className="h-5 w-5 text-violet-700 dark:text-violet-300" aria-hidden />
              Saved event ideas
            </CardTitle>
            <CardDescription>
              Ideas you saved for your stay. They stay here even when they are not in
              today&apos;s picks - manage planning in Plan.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {savedOnlyRecommendations.map((rec) => (
              <div key={`events-saved-only-${rec.id}`} data-testid="events-saved-event-idea">
                <GuestEventRecommendationCard
                  rec={rec}
                  saved
                  savedDetails={savedEventDetails[rec.id]}
                  onToggleSave={onToggleSaveEvent}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {!hasAny ? (
        <Card className="mx-1 md:mx-0">
          <CardContent className="py-10 text-center">
            <CalendarDays className="mx-auto h-10 w-10 text-muted-foreground/60" aria-hidden />
            <p className="mt-3 text-sm text-muted-foreground">
              No event ideas right now. Check Discover for places, or ask your host what&apos;s on
              this week.
            </p>
            <Button type="button" className="mt-4" onClick={onNavigateDiscover}>
              Open Discover
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {feedPicks.length > 0 ? (
        <div className="space-y-3 px-1 md:px-0">
          <h3 className="px-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Regional highlights
          </h3>
          <div className="grid gap-3 md:grid-cols-2">
            {feedPicks.map((rec) => (
              <GuestEventRecommendationCard
                key={rec.id}
                rec={rec}
                saved={savedSet.has(rec.id)}
                savedDetails={savedEventDetails[rec.id]}
                onToggleSave={onToggleSaveEvent}
              />
            ))}
          </div>
        </div>
      ) : null}

      {hostPicks.length > 0 ? (
        <Card className="mx-1 border-emerald-200/60 bg-emerald-50/30 md:mx-0 dark:border-emerald-900/40 dark:bg-emerald-950/15">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <MapPin className="h-5 w-5 text-emerald-700" aria-hidden />
              Host seasonal picks
            </CardTitle>
            <CardDescription>Curated by your host — scored for your group</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {hostPicks.map((rec) => (
              <GuestEventRecommendationCard
                key={rec.id}
                rec={rec}
                saved={savedSet.has(rec.id)}
                savedDetails={savedEventDetails[rec.id]}
                onToggleSave={onToggleSaveEvent}
              />
            ))}
          </CardContent>
        </Card>
      ) : null}

      <div className="flex flex-wrap justify-center gap-3 pb-6">
        {onNavigatePlan ? (
          <Button type="button" onClick={onNavigatePlan}>
            Add to your plan
          </Button>
        ) : null}
        <Button type="button" variant="outline" onClick={onNavigateDiscover}>
          Browse places in Discover
        </Button>
      </div>
    </div>
  );
};
