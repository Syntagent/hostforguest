"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  itinerariesApi,
  type Attraction,
  type GuestGroup,
  type HostItineraryRow,
  type ItineraryWithDetailsDTO,
  type DayPlanDTO,
  type ItineraryActivityDTO,
  type ItineraryMapViewData,
} from "@/lib/api";
import { GoogleMapsProvider } from "@/components/maps/GoogleMapsProvider";
import { InteractiveMap } from "@/components/maps/InteractiveMap";
import { CalendarClock, Loader2, MapPin, Plus, Sparkles, Wand2 } from "lucide-react";

interface RoutesTabProps {
  guestGroups: GuestGroup[];
  attractions: Attraction[];
  onRefresh: () => void;
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function toNaiveLocalIso(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export const RoutesTab: React.FC<RoutesTabProps> = ({
  guestGroups,
  attractions,
  onRefresh,
}) => {
  const [templates, setTemplates] = useState<HostItineraryRow[]>([]);
  const [guestIts, setGuestIts] = useState<HostItineraryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ItineraryWithDetailsDTO | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [mapData, setMapData] = useState<ItineraryMapViewData | null>(null);
  const [mapLoading, setMapLoading] = useState(false);
  const [selectedDayId, setSelectedDayId] = useState<string | null>(null);

  const [showNewTemplate, setShowNewTemplate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newBase, setNewBase] = useState("Lovran, Croatia");

  const [showAi, setShowAi] = useState(false);
  const [aiDays, setAiDays] = useState(3);
  const [aiTheme, setAiTheme] = useState("");
  const [aiInterests, setAiInterests] = useState("culture,nature,food");
  const [aiBusy, setAiBusy] = useState(false);

  const [showAssign, setShowAssign] = useState(false);
  const [assignGroupId, setAssignGroupId] = useState("");
  const [assignStart, setAssignStart] = useState(() => new Date().toISOString().slice(0, 10));
  const [assignBusy, setAssignBusy] = useState(false);

  const [showAddDay, setShowAddDay] = useState(false);
  const [showAddAct, setShowAddAct] = useState(false);
  const [pickAttractionId, setPickAttractionId] = useState("");

  const loadLists = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [tRes, iRes] = await Promise.all([
      itinerariesApi.getTemplates(),
      itinerariesApi.getHostItineraries(),
    ]);
    if (tRes.success && tRes.data) setTemplates(tRes.data);
    else setError(tRes.error || "Failed to load templates");
    if (iRes.success && iRes.data) setGuestIts(iRes.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    void loadLists();
  }, [loadLists]);

  const openDetail = async (row: HostItineraryRow) => {
    setDetailLoading(true);
    setSelected(null);
    setMapData(null);
    const res = await itinerariesApi.getById(row.id, true);
    if (res.success && res.data) {
      setSelected(res.data);
      const firstDay = res.data.day_plans?.[0];
      if (firstDay) {
        setSelectedDayId(firstDay.id);
        await loadMapForDay(firstDay.id);
      } else {
        setSelectedDayId(null);
      }
    } else {
      setError(res.error || "Failed to load itinerary");
    }
    setDetailLoading(false);
  };

  const loadMapForDay = async (dayPlanId: string) => {
    setMapLoading(true);
    const res = await itinerariesApi.getDayPlanMapView(dayPlanId);
    if (res.success && res.data) setMapData(res.data);
    else setMapData(null);
    setMapLoading(false);
  };

  const sortedDays = useMemo(() => {
    if (!selected?.day_plans) return [];
    return [...selected.day_plans].sort((a, b) => a.day_number - b.day_number);
  }, [selected]);

  const currentDay: DayPlanDTO | undefined = useMemo(() => {
    if (!selectedDayId || !sortedDays.length) return sortedDays[0];
    return sortedDays.find((d) => d.id === selectedDayId) || sortedDays[0];
  }, [selectedDayId, sortedDays]);

  const sortedActivities: ItineraryActivityDTO[] = useMemo(() => {
    const acts = currentDay?.activities || [];
    return [...acts].sort((a, b) => a.sequence_order - b.sequence_order);
  }, [currentDay]);

  const mapLocations = useMemo(() => {
    if (!mapData?.locations?.length) return [];
    return mapData.locations.map((l) => ({
      id: l.id,
      title: l.name,
      description: l.type === "base" ? "Base / stay" : "Stop",
      category: l.type,
      location: "",
      rating: 0,
      price: "",
      coordinates: { lat: l.lat, lng: l.lng },
    }));
  }, [mapData]);

  const handleCreateTemplate = async () => {
    if (!newTitle.trim()) return;
    const res = await itinerariesApi.createItinerary(
      {
        title: newTitle.trim(),
        description: newDesc.trim() || null,
        base_location: newBase.trim() || "Lovran, Croatia",
        is_template: true,
      },
      null
    );
    if (res.success) {
      setShowNewTemplate(false);
      setNewTitle("");
      setNewDesc("");
      await loadLists();
      onRefresh();
    } else {
      setError(res.error || "Create failed");
    }
  };

  const handleAiTemplate = async () => {
    setAiBusy(true);
    setError(null);
    const interests = aiInterests
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const sug = await itinerariesApi.generateSuggestions({
      duration_days: aiDays,
      theme_prompt: aiTheme.trim() || null,
      interests,
    });
    if (!sug.success || !sug.data) {
      setError(sug.error || "AI suggestions failed");
      setAiBusy(false);
      return;
    }
    const { suggested_itinerary, day_plans, activities } = sug.data;
    const si = suggested_itinerary as Record<string, unknown>;
    const createBody = {
      title: String(si.title || "AI route"),
      description: (si.description as string) || null,
      start_date: (si.start_date as string) || null,
      end_date: (si.end_date as string) || null,
      base_location: String(si.base_location || "Lovran, Croatia"),
      pace: String(si.pace || "moderate"),
      budget_level: String(si.budget_level || "moderate"),
      transportation_preference: String(si.transportation_preference || "mixed"),
      language: String(si.language || "en"),
      is_template: true,
      group_interests: (si.group_interests as string[]) || interests,
    };
    const cr = await itinerariesApi.createItinerary(createBody, null);
    if (!cr.success || !cr.data) {
      setError(cr.error || "Failed to create template from AI");
      setAiBusy(false);
      return;
    }
    const itineraryId = cr.data.id;
    const dps = day_plans as Record<string, unknown>[];
    const acts = activities as Record<string, unknown>[];
    const D = dps.length || 1;
    const n = acts.length;
    for (let d = 0; d < D; d++) {
      const dp = dps[d];
      const startIdx = Math.floor((d * n) / D);
      const endIdx = Math.floor(((d + 1) * n) / D);
      const slice = acts.slice(startIdx, endIdx);
      const dpr = await itinerariesApi.createDayPlan(itineraryId, dp);
      if (!dpr.success || !dpr.data) continue;
      const dayPlanId = dpr.data.id;
      for (const act of slice) {
        await itinerariesApi.addActivity(dayPlanId, act);
      }
    }
    setShowAi(false);
    setAiBusy(false);
    await loadLists();
    await openDetail(cr.data);
    onRefresh();
  };

  const handleAssign = async () => {
    if (!selected?.is_template || !assignGroupId) return;
    setAssignBusy(true);
    const res = await itinerariesApi.assignTemplate(selected.id, {
      guest_group_id: assignGroupId,
      start_date: assignStart,
    });
    if (res.success && res.data) {
      setShowAssign(false);
      await loadLists();
      setSelected(res.data);
      const firstDay = res.data.day_plans?.[0];
      if (firstDay) {
        setSelectedDayId(firstDay.id);
        await loadMapForDay(firstDay.id);
      }
      onRefresh();
    } else {
      setError(res.error || "Assign failed (group may already have an itinerary)");
    }
    setAssignBusy(false);
  };

  const handleAddDay = async () => {
    if (!selected) return;
    const nextNum = sortedDays.length ? Math.max(...sortedDays.map((d) => d.day_number)) + 1 : 1;
    const baseDate = selected.is_template
      ? new Date(Date.UTC(2000, 0, nextNum))
      : selected.start_date
        ? new Date(selected.start_date + "T12:00:00Z")
        : new Date();
    if (!selected.is_template && selected.start_date) {
      baseDate.setUTCDate(baseDate.getUTCDate() + (nextNum - 1));
    }
    const dateStr = baseDate.toISOString().slice(0, 10);
    const res = await itinerariesApi.createDayPlan(selected.id, {
      day_number: nextNum,
      date: dateStr,
      title: `Day ${nextNum}`,
      theme: "Custom",
    });
    if (res.success) {
      setShowAddDay(false);
      await openDetail(selected as unknown as HostItineraryRow);
      await loadLists();
    } else setError(res.error || "Add day failed");
  };

  const handleAddActivity = async () => {
    if (!selected || !currentDay || !pickAttractionId) return;
    const att = attractions.find((a) => a.id === pickAttractionId);
    if (!att) return;
    const dayDate = currentDay.date;
    const start = new Date(`${dayDate}T09:00:00`);
    const last = sortedActivities[sortedActivities.length - 1];
    if (last?.scheduled_end_time) {
      const t = new Date(last.scheduled_end_time);
      start.setHours(t.getHours(), t.getMinutes(), 0, 0);
      start.setMinutes(start.getMinutes() + 30);
    }
    const end = new Date(start.getTime() + 90 * 60 * 1000);
    const body = {
      title: att.name,
      description: att.description || "",
      activity_type: "attraction",
      location_name: att.name,
      address: att.address || "",
      scheduled_start_time: toNaiveLocalIso(start),
      scheduled_end_time: toNaiveLocalIso(end),
      estimated_duration: 90,
      attraction_id: att.id,
      latitude: att.latitude ?? undefined,
      longitude: att.longitude ?? undefined,
      host_tip: att.host_personal_tip || undefined,
    };
    const res = await itinerariesApi.addActivity(currentDay.id, body);
    if (res.success) {
      setShowAddAct(false);
      setPickAttractionId("");
      await openDetail(selected as unknown as HostItineraryRow);
      if (selectedDayId) await loadMapForDay(selectedDayId);
    } else setError(res.error || "Add activity failed");
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading routes…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Routes & itineraries</h2>
          <p className="text-sm text-muted-foreground">
            Reusable daily routes, AI templates, hourly plans, and map view.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setShowNewTemplate(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New template
          </Button>
          <Button variant="outline" onClick={() => setShowAi(true)}>
            <Wand2 className="mr-2 h-4 w-4" />
            AI planner
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
          <Button variant="ghost" size="sm" className="ml-2 h-7" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Route templates</CardTitle>
              <CardDescription>Share with any guest via Assign</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {templates.length === 0 ? (
                <p className="text-sm text-muted-foreground">No templates yet.</p>
              ) : (
                templates.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => void openDetail(t)}
                    className="flex w-full items-center justify-between rounded-lg border bg-card px-3 py-2 text-left text-sm hover:bg-muted/60"
                  >
                    <span className="font-medium">{t.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {t.total_days}d · {t.base_location}
                    </span>
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Guest itineraries</CardTitle>
              <CardDescription>Linked to a guest group</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {guestIts.length === 0 ? (
                <p className="text-sm text-muted-foreground">No guest itineraries yet.</p>
              ) : (
                guestIts.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => void openDetail(t)}
                    className="flex w-full items-center justify-between rounded-lg border bg-card px-3 py-2 text-left text-sm hover:bg-muted/60"
                  >
                    <span className="font-medium">{t.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {t.start_date} → {t.end_date}
                    </span>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="min-h-[420px]">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <CalendarClock className="h-4 w-4" />
              Detail
            </CardTitle>
          </CardHeader>
          <CardContent>
            {detailLoading && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading…
              </div>
            )}
            {!detailLoading && !selected && (
              <p className="text-sm text-muted-foreground">Select a template or itinerary.</p>
            )}
            {selected && (
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold">{selected.title}</h3>
                  {selected.description && (
                    <p className="mt-1 text-sm text-muted-foreground">{selected.description}</p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selected.is_template && (
                      <>
                        <Button size="sm" onClick={() => setShowAssign(true)}>
                          Assign to guest group
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowAddDay(true)}>
                          Add day
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowAddAct(true)}>
                          Add stop
                        </Button>
                      </>
                    )}
                    {!selected.is_template && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => setShowAddDay(true)}>
                          Add day
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowAddAct(true)}>
                          Add stop
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {sortedDays.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {sortedDays.map((d) => (
                      <Button
                        key={d.id}
                        size="sm"
                        variant={selectedDayId === d.id ? "primary" : "outline"}
                        onClick={() => {
                          setSelectedDayId(d.id);
                          void loadMapForDay(d.id);
                        }}
                      >
                        Day {d.day_number}
                      </Button>
                    ))}
                  </div>
                )}

                <div>
                  <h4 className="mb-2 text-sm font-medium">Hourly plan</h4>
                  <ul className="space-y-2 border-l-2 border-primary/30 pl-3">
                    {sortedActivities.length === 0 ? (
                      <li className="text-sm text-muted-foreground">No activities this day.</li>
                    ) : (
                      sortedActivities.map((a) => (
                        <li key={a.id} className="text-sm">
                          <span className="font-mono text-xs text-muted-foreground">
                            {formatTime(a.scheduled_start_time)} –{" "}
                            {formatTime(a.scheduled_end_time)}
                          </span>
                          <div className="font-medium">{a.title}</div>
                          {a.host_tip && (
                            <p className="text-muted-foreground">Tip: {a.host_tip}</p>
                          )}
                          {a.description && (
                            <p className="text-xs text-muted-foreground">{a.description}</p>
                          )}
                        </li>
                      ))
                    )}
                  </ul>
                </div>

                <div>
                  <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <MapPin className="h-4 w-4" />
                    Map
                  </h4>
                  {mapLoading && (
                    <p className="text-xs text-muted-foreground">Loading map…</p>
                  )}
                  {!mapLoading && mapLocations.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      Add stops with coordinates or linked attractions to see the map.
                    </p>
                  )}
                  {!mapLoading && mapLocations.length > 0 && (
                    <GoogleMapsProvider
                      apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ""}
                    >
                      <div className="h-[280px] overflow-hidden rounded-xl border">
                        <InteractiveMap locations={mapLocations} className="h-full w-full" />
                      </div>
                    </GoogleMapsProvider>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {showNewTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>New route template</CardTitle>
              <CardDescription>Reusable route without dates or guest group</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label htmlFor="rt-title">Title</Label>
                <Input
                  id="rt-title"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Best of Lovran in one day"
                />
              </div>
              <div>
                <Label htmlFor="rt-desc">Description / recommendation</Label>
                <Input
                  id="rt-desc"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="rt-base">Base location</Label>
                <Input
                  id="rt-base"
                  value={newBase}
                  onChange={(e) => setNewBase(e.target.value)}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowNewTemplate(false)}>
                  Cancel
                </Button>
                <Button onClick={() => void handleCreateTemplate()}>Create</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {showAi && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                AI route template
              </CardTitle>
              <CardDescription>Builds a reusable template from your attractions area</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label>Days (1–14)</Label>
                <Input
                  type="number"
                  min={1}
                  max={14}
                  value={aiDays}
                  onChange={(e) => setAiDays(Number(e.target.value) || 1)}
                />
              </div>
              <div>
                <Label>Theme / prompt</Label>
                <Input
                  value={aiTheme}
                  onChange={(e) => setAiTheme(e.target.value)}
                  placeholder="e.g. Culinary coastal day"
                />
              </div>
              <div>
                <Label>Interests (comma-separated)</Label>
                <Input value={aiInterests} onChange={(e) => setAiInterests(e.target.value)} />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAi(false)} disabled={aiBusy}>
                  Cancel
                </Button>
                <Button onClick={() => void handleAiTemplate()} disabled={aiBusy}>
                  {aiBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {showAssign && selected?.is_template && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Assign to guest group</CardTitle>
              <CardDescription>Copies this template to a new itinerary with real dates</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label>Guest group</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={assignGroupId}
                  onChange={(e) => setAssignGroupId(e.target.value)}
                >
                  <option value="">Select…</option>
                  {guestGroups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.group_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="as-start">Trip start date</Label>
                <Input
                  id="as-start"
                  type="date"
                  value={assignStart}
                  onChange={(e) => setAssignStart(e.target.value)}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAssign(false)} disabled={assignBusy}>
                  Cancel
                </Button>
                <Button onClick={() => void handleAssign()} disabled={assignBusy || !assignGroupId}>
                  {assignBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Assign"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {(showAddDay || showAddAct) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>{showAddDay ? "Add day" : "Add stop"}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {showAddDay && (
                <p className="text-sm text-muted-foreground">
                  Adds the next day to this itinerary using template or trip dates.
                </p>
              )}
              {showAddAct && (
                <>
                  <p className="text-sm text-muted-foreground">
                    Day {currentDay?.day_number ?? "—"} — pick an attraction.
                  </p>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={pickAttractionId}
                    onChange={(e) => setPickAttractionId(e.target.value)}
                  >
                    <option value="">Select attraction…</option>
                    {attractions.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </select>
                </>
              )}
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowAddDay(false);
                    setShowAddAct(false);
                  }}
                >
                  Cancel
                </Button>
                {showAddDay && <Button onClick={() => void handleAddDay()}>Add day</Button>}
                {showAddAct && (
                  <Button onClick={() => void handleAddActivity()} disabled={!pickAttractionId}>
                    Add
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
