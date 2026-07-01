"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn, isPlausibleGpsLatLng } from "@/lib/utils";
import { Bell, Home, Languages, MapPin, Printer, RefreshCw, ScrollText } from "lucide-react";
import type { GuestGroup } from "@/lib/api";
import type {
  AccommodationOverview,
  DashboardStatsCard,
  RealtimeUpdateSnippet,
} from "./dashboard-types";

function StatCardSkeleton() {
  return (
    <div
      className="animate-pulse rounded-2xl bg-gradient-to-br from-gray-100 to-gray-200/80 p-6"
      style={{ minHeight: "6.5rem" }}
    >
      <div className="mb-3 h-4 w-24 rounded bg-gray-300/80" />
      <div className="h-8 w-16 rounded bg-gray-300/80" />
    </div>
  );
}

function CompactStatCard({ stat }: { stat: DashboardStatsCard }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium leading-snug text-muted-foreground">{stat.title}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-foreground">{stat.value}</p>
        </div>
        <div className="rounded-xl bg-primary/10 p-2 text-primary [&>svg]:h-4 [&>svg]:w-4">
          {stat.icon}
        </div>
      </div>
      <div className="mt-3 flex min-h-5 items-center justify-between gap-2 text-xs">
        <span className="text-muted-foreground">{stat.description}</span>
        {stat.trend ? (
          <span
            className={cn(
              "font-medium",
              stat.trendUp === false ? "text-red-600" : "text-green-600"
            )}
          >
            {stat.trend}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function ChipList({
  items,
  empty,
  tone = "blue",
  limit = 6,
}: {
  items: string[];
  empty: string;
  tone?: "blue" | "green" | "purple";
  limit?: number;
}) {
  const toneClass = {
    blue: "bg-blue-50 text-blue-700 ring-blue-200",
    green: "bg-green-50 text-green-700 ring-green-200",
    purple: "bg-purple-50 text-purple-700 ring-purple-200",
  }[tone];

  if (!items.length) return <p className="text-sm text-muted-foreground">{empty}</p>;

  return (
    <div className="flex flex-wrap gap-1.5">
      {items.slice(0, limit).map((item) => (
        <span key={item} className={cn("rounded-full px-2.5 py-1 text-xs ring-1", toneClass)}>
          {item}
        </span>
      ))}
      {items.length > limit ? (
        <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
          +{items.length - limit} more
        </span>
      ) : null}
    </div>
  );
}

export const OverviewTab: React.FC<{
  statsCards: DashboardStatsCard[];
  guestGroups: GuestGroup[];
  realtimeUpdates: RealtimeUpdateSnippet[];
  onRefresh: () => void;
  accommodationInfo: AccommodationOverview | null;
  isLoading?: boolean;
}> = ({ statsCards, guestGroups, realtimeUpdates, onRefresh, accommodationInfo, isLoading }) => {
  const property = accommodationInfo?.property;
  const location = property?.location;
  const capacity = property?.capacity;
  const services = accommodationInfo?.services ?? {
    amenities: [] as string[],
    servicesOffered: [] as string[],
    languages: [] as string[],
    specialties: [] as string[],
  };
  const amenities = services.amenities ?? [];
  const servicesOffered = services.servicesOffered ?? [];
  const languages = services.languages ?? [];
  const specialties = services.specialties ?? [];
  const propertyName = property?.name || "Your accommodation";
  const address = location?.address?.trim();
  const city = location?.city?.trim();
  const locationLine =
    address && city && !address.toLowerCase().includes(city.toLowerCase())
      ? `${address}, ${city}`
      : address || city || "";

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col gap-3 rounded-3xl border border-border bg-card p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Overview</p>
          <h2 className="mt-1 truncate text-xl font-semibold text-foreground sm:text-2xl">
            {propertyName}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {locationLine || "Complete the stay profile so guests see accurate property details."}
          </p>
        </div>
        <Link
          href="/host/welcome-kit"
          className="inline-flex w-fit items-center justify-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          <Printer className="h-4 w-4" />
          Welcome Kit
        </Link>
      </div>

      <motion.div
        initial={false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {statsCards.map((stat) => (
              <CompactStatCard key={stat.title} stat={stat} />
            ))}
          </div>
        )}
      </motion.div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(20rem,0.8fr)]">
        <Card className={cn("border-border shadow-sm", isLoading && "animate-pulse")}>
          <CardHeader className="pb-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle>Stay Profile</CardTitle>
                <CardDescription>Core information guests will see first</CardDescription>
              </div>
              <Link
                href="/dashboard?tab=accommodation"
                className="text-sm font-medium text-primary underline-offset-4 hover:underline"
              >
                Edit stay details
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {!property ? (
              <p className="text-sm text-muted-foreground">
                No property details loaded yet. Complete onboarding or refresh the dashboard.
              </p>
            ) : (
              <div className="space-y-5">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl bg-muted/60 p-3">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                      <Home className="h-4 w-4" />
                      Property
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {property.type ?? "Accommodation"} · {capacity?.maxGuests ?? "—"} guests
                      {(capacity?.rooms ?? 0) > 0 ? ` · ${capacity?.rooms} rooms` : ""}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-muted/60 p-3 sm:col-span-2">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                      <MapPin className="h-4 w-4" />
                      Location
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {locationLine || "Location not set"}
                    </p>
                    {location?.coordinates &&
                    isPlausibleGpsLatLng(location.coordinates.lat, location.coordinates.lng) ? (
                      <p className="mt-1 text-xs text-green-700">
                        GPS ready: {Number(location.coordinates.lat).toFixed(4)},{" "}
                        {Number(location.coordinates.lng).toFixed(4)}
                      </p>
                    ) : (
                      <p className="mt-1 text-xs text-amber-700">GPS missing for distance calculations</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <div>
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                      <Bell className="h-4 w-4" />
                      Amenities & Services
                    </div>
                    <ChipList items={amenities} empty="No amenities listed yet" tone="blue" />
                    {servicesOffered.length > 0 ? (
                      <div className="mt-2">
                        <ChipList items={servicesOffered} empty="" tone="green" limit={4} />
                      </div>
                    ) : null}
                  </div>
                  <div>
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                      <Languages className="h-4 w-4" />
                      Languages & Local Strengths
                    </div>
                    <p className="mb-2 text-sm text-muted-foreground">
                      {languages.length > 0 ? languages.join(", ") : "No languages listed"}
                    </p>
                    <ChipList items={specialties} empty="No local specialties listed yet" tone="purple" limit={4} />
                  </div>
                </div>

                {accommodationInfo?.description ? (
                  <div className="rounded-2xl border border-border bg-background p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                      <ScrollText className="h-4 w-4" />
                      Host story
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">{accommodationInfo.description}</p>
                  </div>
                ) : null}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle>Next Useful Actions</CardTitle>
            <CardDescription>Keep the dashboard focused on what matters next</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link
              href="/dashboard?tab=groups"
              className="block rounded-2xl border border-border p-3 transition hover:bg-muted/60 focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <p className="text-sm font-medium text-foreground">Create first guest group</p>
              <p className="mt-1 text-xs text-muted-foreground">Generate an access code for arriving guests.</p>
            </Link>
            <Link
              href="/dashboard?tab=attractions"
              className="block rounded-2xl border border-border p-3 transition hover:bg-muted/60 focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <p className="text-sm font-medium text-foreground">Add local recommendations</p>
              <p className="mt-1 text-xs text-muted-foreground">Build the guide before guests ask for ideas.</p>
            </Link>
            <Link
              href="/dashboard?tab=accommodation"
              className="block rounded-2xl border border-border p-3 transition hover:bg-muted/60 focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <p className="text-sm font-medium text-foreground">Complete stay facts</p>
              <p className="mt-1 text-xs text-muted-foreground">Add amenities, services, photos, and house rules.</p>
            </Link>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="border-border shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle>Recent Guest Groups</CardTitle>
            <CardDescription>Latest groups using your guide</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {guestGroups.slice(0, 3).map((group) => (
                <div
                  key={group.id}
                  className="flex items-center justify-between rounded-2xl bg-muted/60 p-3"
                >
                  <div>
                    <p className="font-medium">{group.group_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {group.group_size} guests • {group.status}
                    </p>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(group.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
              {guestGroups.length === 0 && (
                <div className="rounded-2xl border border-dashed border-border p-4 text-sm text-muted-foreground">
                  No guest groups yet. Use the Guests tab to create your first access code.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Croatian Tourism Updates</CardTitle>
                <CardDescription>Current external context for recommendations</CardDescription>
              </div>
              <Button size="sm" variant="outline" onClick={onRefresh} disabled={isLoading}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {realtimeUpdates.slice(0, 3).map((update, index) => (
                <div key={`${update.id}-${index}`} className="rounded-2xl bg-muted/60 p-3">
                  <p className="text-sm font-medium">{update.title || "Tourism Update"}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                    {update.description || update.content ||
                      "New information available from Croatian tourism sources"}
                  </p>
                  {update.source ? (
                    <p className="mt-1 text-xs text-muted-foreground">Source: {update.source}</p>
                  ) : null}
                </div>
              ))}
              {realtimeUpdates.length === 0 && (
                <div className="rounded-2xl border border-dashed border-border p-4 text-sm text-muted-foreground">
                  No recent tourism updates yet. Refresh later when planning guest recommendations.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
