"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { realtimeApi } from "@/lib/api";
import type { RealtimeUpdateSnippet } from "./dashboard-types";

export type RealtimeUpdateItem = RealtimeUpdateSnippet & {
  source?: string;
  content_type?: string;
  url?: string;
  relevant_cities?: string[];
};

function formatContentType(t: string | undefined) {
  if (!t) return "Update";
  return t.replace(/_/g, " ");
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

  const city = hostCity?.trim() || "Lovran";

  const loadEvents = useCallback(async () => {
    setLoadingEvents(true);
    const res = await realtimeApi.getUpdates(city, "events");
    if (res.success && Array.isArray(res.data)) {
      setEventsOnly(
        res.data.map((u: Record<string, unknown>) => ({
          id: String(u.id),
          title: String(u.title || "Event"),
          content: String(u.content || u.description || ""),
          description: String(u.description || u.content || ""),
          created_at: String(u.created_at || ""),
          source: (u.source_name as string) || (u.source as string) || undefined,
          content_type: String(u.content_type || "events"),
          url: (u.url as string) || undefined,
          relevant_cities: (u.relevant_cities as string[]) || [],
        }))
      );
    }
    const sum = await realtimeApi.getSummary();
    if (sum.success && sum.data) setSummary(sum.data);
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
      setBootstrapMsg(`Feed ready — ${n} events for ${city}.`);
      await loadEvents();
      onRefresh();
    } else {
      setBootstrapMsg(r.error || "Could not refresh event sources.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Events &amp; local happenings</h2>
          <p className="text-sm text-muted-foreground">
            Festivals, markets, and seasonal tips for {city} and Kvarner.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" disabled={loadingEvents} onClick={() => void loadEvents()}>
            {loadingEvents ? "Loading…" : "Reload events"}
          </Button>
          <Button variant="secondary" onClick={() => void handleBootstrap()}>
            Refresh sources
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

      <Card className="bg-gradient-to-br from-blue-50 to-purple-50">
        <CardHeader>
          <CardTitle>Upcoming &amp; seasonal events</CardTitle>
          <CardDescription>
            {rows.length > 0
              ? `${rows.length} items for your area`
              : "No events yet — use Refresh sources."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {rows.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500">
                No events in the feed. Click Refresh sources, then Reload events.
              </p>
            ) : (
              rows.map((update, index) => (
                <article
                  key={`${update.id}-${index}`}
                  className="rounded-lg border border-white/80 bg-white p-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium capitalize text-violet-800">
                      {formatContentType(update.content_type)}
                    </span>
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
                    {update.created_at ? new Date(update.created_at).toLocaleString() : "Recently"}
                  </p>
                </article>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
