"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { BentoGrid } from "@/components/ui/bento-grid";
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

export const OverviewTab: React.FC<{
  statsCards: DashboardStatsCard[];
  guestGroups: GuestGroup[];
  realtimeUpdates: RealtimeUpdateSnippet[];
  onRefresh: () => void;
  accommodationInfo: AccommodationOverview | null;
}> = ({ statsCards, guestGroups, realtimeUpdates, onRefresh, accommodationInfo }) => {
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

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Overview</h2>
        <Link
          href="/host/welcome-kit"
          className="inline-flex items-center gap-2 rounded-lg border-2 border-blue-600 px-4 py-2 text-sm font-semibold text-blue-600 transition-colors hover:bg-blue-600 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          <Printer className="h-4 w-4" />
          Generate Welcome Kit
        </Link>
      </div>

      <motion.div
        initial={false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <BentoGrid
          items={statsCards.map((stat) => ({
            title: stat.title,
            description: `${stat.value} • ${stat.description}`,
            icon: stat.icon,
            className: "bg-gradient-to-br from-blue-50 to-purple-50",
            content: (
              <div className="mt-4 flex items-center justify-between">
                <div className="text-3xl font-bold text-gray-900">{stat.value}</div>
                <div
                  className={cn(
                    "text-sm font-medium",
                    stat.trendUp ? "text-green-600" : "text-red-600"
                  )}
                >
                  {stat.trend}
                </div>
              </div>
            ),
          }))}
          className="grid-cols-1 md:grid-cols-2 xl:grid-cols-4"
        />
      </motion.div>

      <Card className="bg-gradient-to-br from-green-50 to-blue-50">
        <CardHeader>
          <CardTitle>Your Accommodation Details</CardTitle>
          <CardDescription>Property information for personalized guest experiences</CardDescription>
        </CardHeader>
        <CardContent>
          {!property ? (
            <p className="text-sm text-gray-600">
              No property details loaded yet. Complete onboarding or refresh the dashboard.
            </p>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="space-y-4">
                  <div>
                    <h4 className="mb-2 flex items-center gap-2 font-medium text-gray-900">
                      <MapPin className="h-4 w-4" />
                      Location
                    </h4>
                    <div className="space-y-2 text-sm">
                      <p>
                        <span className="font-medium">Address:</span>{" "}
                        {location?.address ?? "—"}
                      </p>
                      <p>
                        <span className="font-medium">City:</span> {location?.city ?? "—"}
                      </p>
                      <p>
                        <span className="font-medium">County:</span> {location?.county ?? "—"}
                      </p>
                      {location?.coordinates &&
                      isPlausibleGpsLatLng(location.coordinates.lat, location.coordinates.lng) ? (
                        <p className="text-green-600">
                          <span className="font-medium">GPS:</span>{" "}
                          {Number(location.coordinates.lat).toFixed(4)},{" "}
                          {Number(location.coordinates.lng).toFixed(4)}
                        </p>
                      ) : (
                        <p className="text-yellow-600">
                          <span className="font-medium">GPS:</span> Not set — needed for
                          distance calculations
                        </p>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="mb-2 flex items-center gap-2 font-medium text-gray-900">
                      <Home className="h-4 w-4" />
                      Property
                    </h4>
                    <div className="space-y-2 text-sm">
                      <p>
                        <span className="font-medium">Name:</span> {property.name ?? "—"}
                      </p>
                      <p>
                        <span className="font-medium">Type:</span> {property.type ?? "—"}
                      </p>
                      <p>
                        <span className="font-medium">Max Guests:</span>{" "}
                        {capacity?.maxGuests ?? "—"}
                      </p>
                      {(capacity?.rooms ?? 0) > 0 && (
                        <p>
                          <span className="font-medium">Rooms:</span> {capacity?.rooms}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <h4 className="mb-2 flex items-center gap-2 font-medium text-gray-900">
                      <Bell className="h-4 w-4" />
                      Services & Amenities
                    </h4>
                    <div className="space-y-2 text-sm">
                      {amenities.length > 0 ? (
                        <div>
                          <p className="font-medium">Amenities:</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {amenities.slice(0, 6).map((amenity, index) => (
                              <span
                                key={index}
                                className="rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-700"
                              >
                                {amenity}
                              </span>
                            ))}
                            {amenities.length > 6 && (
                              <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                                +{amenities.length - 6} more
                              </span>
                            )}
                          </div>
                        </div>
                      ) : (
                        <p className="text-gray-500">No amenities listed</p>
                      )}

                      {servicesOffered.length > 0 && (
                        <div className="mt-3">
                          <p className="font-medium">Services:</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {servicesOffered.slice(0, 4).map((service, index) => (
                              <span
                                key={index}
                                className="rounded-full bg-green-100 px-2 py-1 text-xs text-green-700"
                              >
                                {service}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="mb-2 flex items-center gap-2 font-medium text-gray-900">
                      <Languages className="h-4 w-4" />
                      Languages & Specialties
                    </h4>
                    <div className="space-y-2 text-sm">
                      <p>
                        <span className="font-medium">Languages:</span>{" "}
                        {languages.length > 0
                          ? languages.join(", ")
                          : "—"}
                      </p>
                      {specialties.length > 0 && (
                        <div>
                          <p className="font-medium">Local Specialties:</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {specialties.slice(0, 4).map((specialty, index) => (
                              <span
                                key={index}
                                className="rounded-full bg-purple-100 px-2 py-1 text-xs text-purple-700"
                              >
                                {specialty}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {accommodationInfo?.description ? (
                <div className="mt-6 border-t border-gray-200 pt-4">
                  <h4 className="mb-2 flex items-center gap-2 font-medium text-gray-900">
                    <ScrollText className="h-4 w-4" />
                    Description
                  </h4>
                  <p className="text-sm text-gray-600">{accommodationInfo.description}</p>
                </div>
              ) : null}

              {accommodationInfo?.welcomeMessage ? (
                <div className="mt-4">
                  <h4 className="mb-2 font-medium text-gray-900">Welcome Message</h4>
                  <p className="text-sm italic text-gray-600">
                    &quot;{accommodationInfo.welcomeMessage}&quot;
                  </p>
                </div>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Guest Groups</CardTitle>
            <CardDescription>Your latest guest interactions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {guestGroups.slice(0, 3).map((group) => (
                <div
                  key={group.id}
                  className="flex items-center justify-between rounded-lg bg-gray-50 p-3"
                >
                  <div>
                    <p className="font-medium">{group.group_name}</p>
                    <p className="text-sm text-gray-600">
                      {group.group_size} guests • {group.status}
                    </p>
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(group.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
              {guestGroups.length === 0 && (
                <p className="py-4 text-center text-gray-500">
                  No guest groups yet. Create your first access code!
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Croatian Tourism Updates</CardTitle>
                <CardDescription>Latest insights from Croatian tourism sources</CardDescription>
              </div>
              <Button size="sm" variant="outline" onClick={onRefresh}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {realtimeUpdates.slice(0, 3).map((update, index) => (
                <div
                  key={`${update.id}-${index}`}
                  className="rounded-lg bg-gradient-to-r from-blue-50 to-purple-50 p-3"
                >
                  <p className="text-sm font-medium">{update.title || "Tourism Update"}</p>
                  <p className="mt-1 text-sm text-gray-600">
                    {update.description ||
                      "New information available from Croatian tourism sources"}
                  </p>
                </div>
              ))}
              {realtimeUpdates.length === 0 && (
                <p className="py-4 text-center text-gray-500">
                  No recent updates. Check back later for Croatian tourism insights!
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
