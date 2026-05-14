"use client";

import React, { useEffect, useRef, useState } from "react";
import { useGoogleMaps } from "./GoogleMapsProvider";
import { motion } from "framer-motion";

interface Location {
  id: string;
  title: string;
  description: string;
  category: string;
  location: string;
  rating: number;
  price: string;
  coordinates: {
    lat: number;
    lng: number;
  };
  hostTip?: string;
  weatherDependent?: boolean;
  image?: string;
}

interface InteractiveMapProps {
  locations: Location[];
  onLocationSelect?: (location: Location) => void;
  selectedLocationId?: string;
  className?: string;
}

const CROATIA_CENTER = { lat: 45.1, lng: 15.2 };
const CROATIA_BOUNDS = {
  north: 46.5,
  south: 42.4,
  east: 19.4,
  west: 13.5
};

export const InteractiveMap: React.FC<InteractiveMapProps> = ({
  locations,
  onLocationSelect,
  selectedLocationId,
  className = ""
}) => {
  const { isLoaded, google, setMap } = useGoogleMaps();
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMapInstance] = useState<google.maps.Map | null>(null);
  const [markers, setMarkers] = useState<google.maps.Marker[]>([]);
  const [infoWindow, setInfoWindow] = useState<google.maps.InfoWindow | null>(null);

  // Initialize map
  useEffect(() => {
    if (!isLoaded || !google || !mapRef.current) return;

    const mapInstance = new google.maps.Map(mapRef.current, {
      center: CROATIA_CENTER,
      zoom: 7,
      mapTypeId: google.maps.MapTypeId.ROADMAP,
      mapTypeControl: true,
      streetViewControl: true,
      fullscreenControl: true,
      zoomControl: true,
      styles: [
        {
          featureType: "poi",
          elementType: "labels",
          stylers: [{ visibility: "off" }]
        }
      ]
    });

    // Restrict map to Croatia
    mapInstance.setOptions({
      restriction: {
        latLngBounds: CROATIA_BOUNDS,
        strictBounds: false
      }
    });

    setMapInstance(mapInstance);
    setMap(mapInstance);

    // Create info window
    const infoWindowInstance = new google.maps.InfoWindow();
    setInfoWindow(infoWindowInstance);

    return () => {
      setMap(null);
    };
  }, [isLoaded, google, setMap]);

  // Create markers for locations
  useEffect(() => {
    if (!map || !google || !infoWindow) return;

    // Clear existing markers
    markers.forEach(marker => marker.setMap(null));

    const newMarkers: google.maps.Marker[] = [];

    locations.forEach((location) => {
      const marker = new google.maps.Marker({
        position: location.coordinates,
        map: map,
        title: location.title,
        icon: {
          url: getMarkerIcon(location.category),
          scaledSize: new google.maps.Size(32, 32),
          origin: new google.maps.Point(0, 0),
          anchor: new google.maps.Point(16, 32)
        },
        animation: selectedLocationId === location.id
          ? google.maps.Animation.BOUNCE
          : undefined
      });

      // Add click listener
      marker.addListener("click", () => {
        const content = createInfoWindowContent(location);
        infoWindow.setContent(content);
        infoWindow.open(map, marker);

        if (onLocationSelect) {
          onLocationSelect(location);
        }
      });

      newMarkers.push(marker);
    });

    setMarkers(newMarkers);

    // Fit bounds to show all markers
    if (newMarkers.length > 0) {
      const bounds = new google.maps.LatLngBounds();
      newMarkers.forEach(marker => {
        bounds.extend(marker.getPosition()!);
      });
      map.fitBounds(bounds);
    }

    return () => {
      newMarkers.forEach(marker => marker.setMap(null));
    };
  }, [map, google, infoWindow, locations, selectedLocationId, onLocationSelect]);

  const getMarkerIcon = (category: string): string => {
    const iconMap: Record<string, string> = {
      "Nature & Parks": "🏞️",
      "Culture & History": "🏛️",
      "Food & Wine": "🍽️",
      "Adventure & Sports": "🏃",
      "Relaxation & Wellness": "🧘",
      "Shopping & Markets": "🛍️",
      "Nightlife & Entertainment": "🍷",
      "Photography": "📸"
    };

    // Return a data URL for the emoji icon
    const emoji = iconMap[category] || "📍";
    return `data:image/svg+xml;base64,${btoa(`
      <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
        <circle cx="16" cy="16" r="16" fill="#3B82F6" opacity="0.9"/>
        <text x="16" y="20" text-anchor="middle" font-size="16" fill="white">${emoji}</text>
      </svg>
    `)}`;
  };

  const createInfoWindowContent = (location: Location): string => {
    return `
      <div style="min-width: 200px; padding: 8px;">
        <h3 style="margin: 0 0 8px 0; color: #1F2937; font-size: 16px; font-weight: 600;">
          ${location.title}
        </h3>
        <p style="margin: 0 0 8px 0; color: #6B7280; font-size: 14px;">
          ${location.description.substring(0, 100)}${location.description.length > 100 ? '...' : ''}
        </p>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="background: #E5E7EB; padding: 2px 8px; border-radius: 12px; font-size: 12px; color: #374151;">
            ${location.category}
          </span>
          <span style="color: #059669; font-weight: 600; font-size: 14px;">
            ${location.price}
          </span>
        </div>
        <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 8px;">
          <span style="color: #F59E0B;">⭐</span>
          <span style="color: #6B7280; font-size: 14px;">${location.rating}</span>
        </div>
        ${location.hostTip ? `
          <div style="background: #DBEAFE; padding: 8px; border-radius: 6px; margin-top: 8px;">
            <p style="margin: 0; color: #1E40AF; font-size: 12px; font-style: italic;">
              💡 <strong>Host Tip:</strong> ${location.hostTip}
            </p>
          </div>
        ` : ''}
      </div>
    `;
  };

  if (!isLoaded) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className={`flex items-center justify-center bg-gray-100 rounded-lg ${className}`}
        style={{ minHeight: "400px" }}
      >
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading Croatian map...</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className={`relative ${className}`}
    >
      <div
        ref={mapRef}
        className="w-full h-96 rounded-lg shadow-lg"
        style={{ minHeight: "400px" }}
      />

      {/* Map Controls Overlay */}
      <div className="absolute top-4 left-4 bg-white rounded-lg shadow-md p-2">
        <div className="text-sm font-medium text-gray-700 mb-2">Croatian Attractions</div>
        <div className="text-xs text-gray-500">
          {locations.length} locations available
        </div>
      </div>
    </motion.div>
  );
};
