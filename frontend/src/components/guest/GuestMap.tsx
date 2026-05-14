"use client";

import React, { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Button } from "@/components/ui/button";
import { mapsUrlForAttraction, type Attraction } from "@/lib/api";

/** Fix default marker assets when bundling with webpack/Next. */
function ensureDefaultIcons() {
  if (typeof window === "undefined") return;
  const proto = L.Icon.Default.prototype as unknown as { _getIconUrl?: string };
  delete proto._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  });
}

export type GuestMapMarker = {
  id: string;
  lat: number;
  lng: number;
  title: string;
  subtitle?: string;
  category?: string;
  attraction?: Attraction;
};

function FitBounds({
  points,
  padding,
}: {
  points: [number, number][];
  padding: [number, number];
}) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    if (points.length === 1) {
      map.setView(points[0], 13);
      return;
    }
    const b = L.latLngBounds(points);
    map.fitBounds(b, { padding, maxZoom: 14 });
  }, [map, points, padding]);
  return null;
}

export interface GuestMapProps {
  markers: GuestMapMarker[];
  hostMarker?: { lat: number; lng: number; title?: string } | null;
  className?: string;
  /** Called when user taps "View details" in popup — parent opens sheet */
  onOpenDetails?: (id: string) => void;
}

export const GuestMap: React.FC<GuestMapProps> = ({
  markers,
  hostMarker,
  className,
  onOpenDetails,
}) => {
  useEffect(() => {
    ensureDefaultIcons();
  }, []);

  const points: [number, number][] = useMemo(() => {
    const ps: [number, number][] = markers.map((m) => [m.lat, m.lng]);
    if (hostMarker) ps.push([hostMarker.lat, hostMarker.lng]);
    return ps;
  }, [markers, hostMarker]);

  const center: [number, number] =
    points.length > 0 ? points[0] : [44.5, 15.5];

  const hostIcon = useMemo(
    () =>
      L.divIcon({
        className: "guest-map-host-icon",
        html: `<div style="width:28px;height:28px;border-radius:8px;background:#0ea5e9;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;font-size:14px;">🏠</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      }),
    []
  );

  return (
    <MapContainer
      center={center}
      zoom={points.length ? 11 : 7}
      className={className}
      scrollWheelZoom
      style={{ height: "100%", width: "100%", minHeight: "280px" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.length > 0 ? <FitBounds points={points} padding={[48, 48]} /> : null}

      {hostMarker ? (
        <Marker position={[hostMarker.lat, hostMarker.lng]} icon={hostIcon}>
          <Popup>
            <div className="max-w-[200px] text-sm font-medium">
              {hostMarker.title || "Your stay"}
            </div>
          </Popup>
        </Marker>
      ) : null}

      {markers.map((m) => (
        <Marker key={m.id} position={[m.lat, m.lng]}>
          <Popup>
            <div className="max-w-[220px] space-y-2">
              <div>
                <p className="font-semibold text-foreground">{m.title}</p>
                {m.subtitle ? (
                  <p className="text-xs text-muted-foreground">{m.subtitle}</p>
                ) : null}
                {m.category ? (
                  <p className="mt-0.5 text-xs capitalize text-muted-foreground">{m.category}</p>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-1">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs"
                  disabled={!mapsUrlForAttraction(m.attraction)}
                  onClick={() => openAttractionInMapsSafe(m.attraction)}
                >
                  Directions
                </Button>
                {onOpenDetails ? (
                  <Button
                    type="button"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => onOpenDetails(m.id)}
                  >
                    Details
                  </Button>
                ) : null}
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

function openAttractionInMapsSafe(a?: Attraction) {
  const url = mapsUrlForAttraction(a);
  if (url) window.open(url, "_blank", "noopener,noreferrer");
}
