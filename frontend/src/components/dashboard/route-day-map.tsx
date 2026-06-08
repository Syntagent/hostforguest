"use client";

import { GoogleMapsProvider } from "@/components/maps/GoogleMapsProvider";
import { InteractiveMap, type Location as MapLocation } from "@/components/maps/InteractiveMap";

interface RouteDayMapProps {
  apiKey: string;
  locations: MapLocation[];
  draggableLocationIds: string[];
  onMapClick?: (coords: { lat: number; lng: number }) => void;
  onMarkerDragEnd: (location: MapLocation, coords: { lat: number; lng: number }) => void;
  initialCenter?: { lat: number; lng: number };
  initialZoom?: number;
}

export function RouteDayMap({
  apiKey,
  locations,
  draggableLocationIds,
  onMapClick,
  onMarkerDragEnd,
  initialCenter,
  initialZoom,
}: RouteDayMapProps) {
  return (
    <GoogleMapsProvider apiKey={apiKey}>
      <div className="h-[280px] overflow-hidden rounded-xl border">
        <InteractiveMap
          locations={locations}
          className="h-full w-full"
          onMapClick={onMapClick}
          draggableLocationIds={draggableLocationIds}
          onMarkerDragEnd={onMarkerDragEnd}
          initialCenter={initialCenter}
          initialZoom={initialZoom}
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Drag route markers near another stop to reorder them. Toggle "Add from map" and click
        anywhere on the map to create a waypoint.
      </p>
    </GoogleMapsProvider>
  );
}
