"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { realtimeApi, type EventSourceHealth, type EventSourceProposal } from "@/lib/api";
import type { RealtimeUpdateSnippet } from "./dashboard-types";

export type RealtimeUpdateItem = RealtimeUpdateSnippet & {
  source?: string;
  content_type?: string;
  url?: string;
  relevant_cities?: string[];
  start_at?: string;
  end_at?: string;
  is_demo_seed?: boolean;
};

function formatContentType(t: string | undefined) {
  if (!t) return "Update";
  return t.replace(/_/g, " ");
}

function formatEventDates(start?: string, end?: string) {
  if (!start) return null;
  try {
    const s = new Date(start);
    const e = end ? new Date(end) : null;
    const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" };
    if (e && e.getTime() !== s.getTime()) {
      return `${s.toLocaleDateString(undefined, opts)} – ${e.toLocaleDateString(undefined, opts)}`;
    }
    return s.toLocaleDateString(undefined, opts);
  } catch {
    return null;
  }
}

export const InsightsTab: React.FC<{
  realtimeUpdates: RealtimeUpdateItem[];
  onRefresh: () => void;
  hostCity?: string | null;
}> = ({ realtimeUpdates, onRefresh, hostCity }) => {
  const [eventsOnly, setEventsOnly] = useState<RealtimeUpdateItem[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [bootstrapMsg, setBootstrapMsg] = useState<string | null>(null);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [sourceHealth, setSourceHealth] = useState<EventSourceHealth[]>([]);
  const [proposals, setProposals] = useState<EventSourceProposal[]>([]);
  const [discoverMsg, setDiscoverMsg] = useState<string | null>(null);

  const city = hostCity?.trim() || "Lovran";

  const loadEvents = useCallback(async () => {
    setLoadingEvents(true);
    const res = await realtimeApi.getEvents(city, 720);
    if (res.success && Array.isArray(res.data)) {
      setEventsOnly(
        res.data.map((u: Record<string, unknown>) => ({
          id: String(u.id),
          title: String(u.title || "Event"),
          content: String(u.content || u.description || ""),
          description: String(u.description || u.content || ""),
          created_at: String(u.created_at || ""),
          start_at: (u.start_at as string) || undefined,
          end_at: (u.end_at as string) || undefined,
          source: (u.source_name as string) || (u.source as string) || undefined,
          content_type: String(u.content_type || "events"),
          url: (u.url as string) || undefined,
          relevant_cities: (u.relevant_cities as string[]) || [],
          is_demo_seed: Boolean(u.is_demo_seed),
        }))
      );
    }
    const [sum, health, prop] = await Promise.all([
      realtimeApi.getSummary(),
      realtimeApi.getSourcesHealth(),
      realtimeApi.getSourceProposals("pending"),
    ]);
    if (sum.success && sum.data) setSummary(sum.data);
    if (health.success && Array.isArray(health.data)) setSourceHealth(health.data);
    if (prop.success && Array.isArray(prop.data)) setProposals(prop.data);
    setLoadingEvents(false);
  }, [city]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  const display = eventsOnly.length > 0 ? eventsOnly : realtimeUpdates;
  const rows =
    display.filter(
      (u) => !u.content_type || u.content_type === "events" || u.content_type.includes("event")
    ).length > 0
      ? display.filter(
          (u) =>
            !u.content_type || u.content_type === "events" || u.content_type.includes("event")
        )
      : display;

  const handleBootstrap = async () => {
    setBootstrapMsg(null);
    const r = await realtimeApi.bootstrapEvents(city);
    if (r.success && r.data) {
      const n = (r.data as { events_available?: number }).events_available ?? 0;
      setBootstrapMsg(`Feed synced — ${n} events for ${city}.`);
      await loadEvents();
      onRefresh();
    } else {
      setBootstrapMsg(r.error || "Could not refresh event sources.");
    }
  };

  const handleDiscover = async () => {
    setDiscoverMsg(null);
    const r = await realtimeApi.discoverSources();
    if (r.success && r.data) {
      const n = (r.data as { proposals_created?: number }).proposals_created ?? 0;
      setDiscoverMsg(`Found ${n} suggested sources for your area.`);
      const prop = await realtimeApi.getSourceProposals("pending");
      if (prop.success && Array.isArray(prop.data)) setProposals(prop.data);
    } else {
      setDiscoverMsg(r.error || "Discovery failed.");
    }
  };

  const handleProposal = async (id: string, action: "approve" | "reject") => {
    const fn =
      action === "approve" ? realtimeApi.approveProposal : realtimeApi.rejectProposal;
    await fn(id);
    const prop = await realtimeApi.getSourceProposals("pending");
    if (prop.success && Array.isArray(prop.data)) setProposals(prop.data);
    if (action === "approve") await handleBootstrap();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Events &amp; local happenings</h2>
          <p className="text-sm text-muted-foreground">
            Live calendars for {city} and Croatia — synced from tourist boards.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" disabled={loadingEvents} onClick={() => void loadEvents()}>
            {loadingEvents ? "Loading…" : "Reload events"}
          </Button>
          <Button variant="secondary" onClick={() => void handleBootstrap()}>
            Sync sources
          </Button>
          <Button variant="outline" onClick={() => void handleDiscover()}>
            Discover sources
          </Button>
          <Button variant="outline" onClick={onRefresh}>
            Sync dashboard
          </Button>
        </div>
      </div>

      {summary ? (
        <p className="text-xs text-muted-foreground">
          Sources: {String(summary.active_sources ?? 0)} active · Updates (24h):{" "}
          {String(summary.recent_updates_24h ?? 0)}
        </p>
      ) : null}
      {bootstrapMsg ? (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {bootstrapMsg}
        </p>
      ) : null}
      {discoverMsg ? (
        <p className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
          {discoverMsg}
        </p>
      ) : null}

      {sourceHealth.length > 0 ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Source health</CardTitle>
            <CardDescription>Scrape status for event calendars</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {sourceHealth.map((s) => (
              <div
                key={s.source_id}
                className="flex flex-col gap-1 rounded-md border border-gray-100 bg-gray-50/80 px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="font-medium text-gray-900">{s.name}</span>
                <span className="text-xs text-gray-600">
                  {s.maintenance_hint ? (
                    <span className="text-amber-700">{s.maintenance_hint}</span>
                  ) : (s.consecutive_failures ?? 0) > 0 ? (
                    <span className="text-amber-700">Issues · {s.last_error || "check logs"}</span>
                  ) : (
                    <span className="text-emerald-700">
                      OK · last {s.last_scraped ? new Date(s.last_scraped).toLocaleString() : "never"}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {proposals.length > 0 ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Suggested sources</CardTitle>
            <CardDescription>Approve calendars to monitor for your area</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {proposals.map((p) => (
              <div key={p.id} className="rounded-lg border border-gray-200 bg-white p-3">
                <p className="font-medium text-gray-900">{p.proposed_name}</p>
                <a
                  href={p.proposed_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline"
                >
                  {p.proposed_url}
                </a>
                {p.reasoning ? (
                  <p className="mt-1 text-xs text-gray-600">{p.reasoning}</p>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => void handleProposal(p.id, "approve")}>
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void handleProposal(p.id, "reject")}
                  >
                    Reject
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Card className="bg-gradient-to-br from-blue-50 to-purple-50">
        <CardHeader>
          <CardTitle>Upcoming &amp; seasonal events</CardTitle>
          <CardDescription>
            {rows.length > 0
              ? `${rows.length} items for your area`
              : "No events yet — use Sync sources."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {rows.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500">
                No events in the feed. Click Sync sources, then Reload events.
              </p>
            ) : (
              rows.map((update, index) => {
                const dates = formatEventDates(update.start_at, update.end_at);
                return (
                  <article
                    key={`${update.id}-${index}`}
                    className="rounded-lg border border-white/80 bg-white p-4 shadow-sm"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium capitalize text-violet-800">
                        {formatContentType(update.content_type)}
                      </span>
                      {update.is_demo_seed ? (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-900">
                          Demo
                        </span>
                      ) : null}
                      {dates ? (
                        <span className="text-xs font-medium text-gray-700">{dates}</span>
                      ) : null}
                      {update.relevant_cities?.length ? (
                        <span className="text-xs text-gray-500">
                          {update.relevant_cities.join(", ")}
                        </span>
                      ) : null}
                    </div>
                    <h3 className="mt-2 font-medium text-gray-900">
                      {update.url ? (
                        <a
                          href={update.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-primary hover:underline"
                        >
                          {update.title || "Event"}
                        </a>
                      ) : (
                        update.title || "Event"
                      )}
                    </h3>
                    <p className="mt-1 line-clamp-3 text-sm text-gray-600">
                      {update.description || update.content || "—"}
                    </p>
                    <p className="mt-2 text-xs text-gray-500">
                      Source: {update.source || "Croatian tourism"} ·{" "}
                      {update.created_at
                        ? new Date(update.created_at).toLocaleString()
                        : "Recently"}
                    </p>
                  </article>
                );
              })
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
