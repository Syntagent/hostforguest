"use client";

import React, { useState, useEffect, useRef, useImperativeHandle, useCallback } from "react";
import { motion } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Crosshair, Plus, X, Star, MapPin, Clock, Phone, Globe, Landmark,
  Utensils, Coffee, ShoppingBag, Wine, Tent, Waves, Mountain, Castle, Church, Trees, Theater, Music, Activity
} from "lucide-react";
import { useGoogleMaps } from "./GoogleMapsProvider";
import { Attraction } from "@/lib/api";

interface HostMapViewProps {
  attractions: Attraction[];
  onSelectAttraction: (attraction: Attraction) => void;
  onAddNewAttraction: () => void;
  className?: string;
  hideTitle?: boolean;
  embedded?: boolean;
  selectedAttractionId?: string | null;
}

export interface HostMapViewHandle {
  fitToAttractions: () => void;
}

interface MapMarker {
  id: string;
  position: google.maps.LatLngLiteral;
  title: string;
  attraction: Attraction;
  marker: google.maps.Marker;
  infoWindow: google.maps.InfoWindow;
}

const getCategoryIconComponent = (category: string | undefined, className: string = "h-5 w-5 text-sky-600") => {
  const cat = (category || "other").toLowerCase();
  if (cat.includes("restaurant") || cat.includes("dining") || cat.includes("culinary")) return <Utensils className={className} />;
  if (cat.includes("cafe") || cat.includes("coffee")) return <Coffee className={className} />;
  if (cat.includes("shopping") || cat.includes("market")) return <ShoppingBag className={className} />;
  if (cat.includes("wine") || cat.includes("winery")) return <Wine className={className} />;
  if (cat.includes("nature") || cat.includes("park") || cat.includes("trees")) return <Trees className={className} />;
  if (cat.includes("beach") || cat.includes("sea") || cat.includes("water")) return <Waves className={className} />;
  if (cat.includes("mountain") || cat.includes("hiking") || cat.includes("trail")) return <Mountain className={className} />;
  if (cat.includes("castle") || cat.includes("fort")) return <Castle className={className} />;
  if (cat.includes("church") || cat.includes("cathedral")) return <Church className={className} />;
  if (cat.includes("museum") || cat.includes("art") || cat.includes("gallery")) return <Theater className={className} />;
  if (cat.includes("event") || cat.includes("festival") || cat.includes("music")) return <Music className={className} />;
  if (cat.includes("activity") || cat.includes("adventure") || cat.includes("sport")) return <Activity className={className} />;
  if (cat.includes("accommodation") || cat.includes("hotel") || cat.includes("camp")) return <Tent className={className} />;
  
  return <Landmark className={className} />;
};

export const HostMapView = React.forwardRef<HostMapViewHandle, HostMapViewProps>(
  (
    {
      attractions,
      onSelectAttraction,
      onAddNewAttraction,
      className,
      hideTitle = false,
      embedded = false,
      selectedAttractionId = null,
    },
    ref
  ) => {
  const { isLoaded, google, map, setMap } = useGoogleMaps();
  const mapRef = useRef<HTMLDivElement>(null);
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [selectedMarker, setSelectedMarker] = useState<MapMarker | null>(null);
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<string | null>(null);

  // Initialize map when Google Maps is loaded
  useEffect(() => {
    if (!isLoaded || !google || !mapRef.current || map) return;

    const initialPosition = { lat: 45.2923, lng: 14.2747 }; // Lovran, Croatia

    const newMap = new google.maps.Map(mapRef.current, {
      center: initialPosition,
      zoom: 12,
      mapTypeId: google.maps.MapTypeId.ROADMAP,
      mapTypeControl: true,
      mapTypeControlOptions: {
        position: google.maps.ControlPosition.TOP_RIGHT,
        style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
      },
      streetViewControl: true,
      streetViewControlOptions: {
        position: google.maps.ControlPosition.RIGHT_BOTTOM,
      },
      fullscreenControl: true,
      fullscreenControlOptions: {
        position: google.maps.ControlPosition.RIGHT_TOP,
      },
      zoomControl: true,
      zoomControlOptions: {
        position: google.maps.ControlPosition.RIGHT_BOTTOM,
      },
      styles: [
        {
          featureType: "poi",
          elementType: "labels",
          stylers: [{ visibility: "off" }]
        }
      ]
    });

    setMap(newMap);
  }, [isLoaded, google, map, setMap]);

  // Create markers for attractions
  useEffect(() => {
    if (!map || !google || attractions.length === 0) return;

    // Clear existing markers
    setMarkers((previousMarkers) => {
      previousMarkers.forEach((marker) => {
        marker.marker.setMap(null);
        marker.infoWindow.close();
      });
      return [];
    });

    const createdMarkers: MapMarker[] = [];

    // Filter attractions if a category is selected
    const attractionsToMap = activeCategoryFilter
      ? attractions.filter(a => {
          const cat = a.category || a.attraction_type || '';
          return cat === activeCategoryFilter;
        })
      : attractions;

    const getMarkerColor = (category: string): string => {
      const cat = (category || "other").toLowerCase();
      
      if (cat.includes("historic") || cat.includes("castle")) return "#f59e0b"; // Amber
      if (cat.includes("museum") || cat.includes("art") || cat.includes("cultur")) return "#8b5cf6"; // Purple
      if (cat.includes("restaurant") || cat.includes("dining") || cat.includes("culinary")) return "#ef4444"; // Red
      if (cat.includes("cafe") || cat.includes("coffee")) return "#f97316"; // Orange
      if (cat.includes("nature") || cat.includes("park") || cat.includes("trees")) return "#10b981"; // Emerald
      if (cat.includes("beach") || cat.includes("sea") || cat.includes("water")) return "#0ea5e9"; // Sky blue
      if (cat.includes("shop") || cat.includes("market")) return "#ec4899"; // Pink
      if (cat.includes("church") || cat.includes("cathedral")) return "#64748b"; // Slate
      if (cat.includes("hike") || cat.includes("trail") || cat.includes("mountain")) return "#14b8a6"; // Teal
      if (cat.includes("wine")) return "#db2777"; // Deep Pink
      if (cat.includes("event") || cat.includes("festival") || cat.includes("music")) return "#d946ef"; // Fuchsia
      if (cat.includes("activit") || cat.includes("adventure") || cat.includes("sport")) return "#f97316"; // Orange
      if (cat.includes("wellness") || cat.includes("spa")) return "#06b6d4"; // Cyan
      if (cat.includes("accommodation") || cat.includes("hotel") || cat.includes("camp")) return "#8b5cf6"; // Purple

      return "#3b82f6"; // Default Blue
    };

    const addMarkerForAttraction = (attraction: Attraction, position: google.maps.LatLngLiteral) => {
      const category = attraction.category || attraction.attraction_type || "Other";
      const markerColor = getMarkerColor(category);
      const isSelected = activeCategoryFilter === null || activeCategoryFilter === category;
      
      const svgIcon = {
        path: "M12 0C7.58 0 4 3.58 4 8c0 5.25 8 13 8 13s8-7.75 8-13c0-4.42-3.58-8-8-8zm0 11.5c-1.93 0-3.5-1.57-3.5-3.5S10.07 4.5 12 4.5 15.5 6.07 15.5 8 13.93 11.5 12 11.5z",
        fillColor: markerColor,
        fillOpacity: isSelected ? 1 : 0.4,
        strokeWeight: 1.5,
        strokeColor: "#ffffff",
        rotation: 0,
        scale: 1.6,
        anchor: new google.maps.Point(12, 21),
        labelOrigin: new google.maps.Point(12, 8),
      };

      const marker = new google.maps.Marker({
        position,
        map,
        title: attraction.name,
        icon: svgIcon,
        label: {
          text: getMarkerIcon(category),
          fontSize: "14px", // Adjusted for emojis
          color: "#ffffff",
          fontWeight: "normal",
        },
        opacity: isSelected ? 1 : 0.4,
        zIndex: isSelected ? 100 : 1,
        animation: google.maps.Animation.DROP,
      });

      const infoWindow = new google.maps.InfoWindow({
        content: createInfoWindowContent(attraction),
      });

      marker.addListener("click", () => {
        createdMarkers.forEach((m) => m.infoWindow.close());
        // We now rely on the bottom card instead of the default info window for a cleaner look
        // infoWindow.open(map, marker);
        setSelectedMarker({
          id: attraction.id,
          position,
          title: attraction.name,
          attraction,
          marker,
          infoWindow,
        });
      });

      const mapMarker: MapMarker = {
        id: attraction.id,
        position,
        title: attraction.name,
        attraction,
        marker,
        infoWindow,
      };

      createdMarkers.push(mapMarker);
      setMarkers((prev) => [...prev, mapMarker]);
    };

    attractionsToMap.forEach((attraction) => {
      if (
        typeof attraction.latitude === "number" &&
        Number.isFinite(attraction.latitude) &&
        typeof attraction.longitude === "number" &&
        Number.isFinite(attraction.longitude)
      ) {
        addMarkerForAttraction(attraction, {
          lat: attraction.latitude,
          lng: attraction.longitude,
        });
        return;
      }

      if (
        Array.isArray(attraction.coordinates) &&
        attraction.coordinates.length === 2 &&
        Number.isFinite(attraction.coordinates[0]) &&
        Number.isFinite(attraction.coordinates[1])
      ) {
        const [first, second] = attraction.coordinates;
        const latLng =
          Math.abs(first) <= 90 && Math.abs(second) <= 180
            ? { lat: first, lng: second }
            : { lat: second, lng: first };

        addMarkerForAttraction(attraction, latLng);
        return;
      }

      if (!attraction.location?.trim()) {
        return;
      }

      const geocoder = new google.maps.Geocoder();
      geocoder.geocode({ address: attraction.location }, (results, status) => {
        if (status !== google.maps.GeocoderStatus.OK || !results?.[0]) {
          return;
        }

        const location = results[0].geometry.location;
        addMarkerForAttraction(attraction, { lat: location.lat(), lng: location.lng() });
      });
    });

    return () => {
      createdMarkers.forEach((marker) => {
        marker.marker.setMap(null);
        marker.infoWindow.close();
      });
    };
  }, [map, google, attractions, activeCategoryFilter]);

  // Handle external selection
  useEffect(() => {
    if (!map || !google || markers.length === 0 || !selectedAttractionId) return;

    const markerToSelect = markers.find((m) => m.id === selectedAttractionId);
    if (markerToSelect) {
      setSelectedMarker(markerToSelect);
      map.panTo(markerToSelect.position);
      map.setZoom(16);
    }
  }, [map, google, markers, selectedAttractionId]);

    const getMarkerIcon = (category: string): string => {
      const cat = (category || "other").toLowerCase();
      if (cat.includes("restaurant") || cat.includes("dining") || cat.includes("culinary")) return "🍽️";
      if (cat.includes("cafe") || cat.includes("coffee")) return "☕";
      if (cat.includes("shop") || cat.includes("market")) return "🛍️";
      if (cat.includes("wine")) return "🍷";
      if (cat.includes("nature") || cat.includes("park") || cat.includes("trees")) return "🌲";
      if (cat.includes("beach") || cat.includes("sea") || cat.includes("water")) return "🏖️";
      if (cat.includes("hike") || cat.includes("trail") || cat.includes("mountain")) return "🥾";
      if (cat.includes("castle") || cat.includes("historic")) return "🏰";
      if (cat.includes("church") || cat.includes("cathedral")) return "⛪";
      if (cat.includes("museum") || cat.includes("art") || cat.includes("cultur")) return "🎭";
      if (cat.includes("event") || cat.includes("festival") || cat.includes("music")) return "🎵";
      if (cat.includes("activit") || cat.includes("adventure") || cat.includes("sport")) return "🧗";
      if (cat.includes("wellness") || cat.includes("spa")) return "🧘";
      if (cat.includes("accommodation") || cat.includes("hotel") || cat.includes("camp")) return "⛺";
      
      return "📍";
    };

  const getMarkerColor = (category: string): string => {
    const colorMap: Record<string, string> = {
      "Historical": "#f59e0b", // Amber
      "Historical Site": "#f59e0b", // Amber
      "Museum": "#8b5cf6", // Purple
      "Dining": "#ef4444", // Red
      "Restaurant": "#ef4444", // Red
      "Cafe": "#f97316", // Orange
      "Nature": "#10b981", // Emerald
      "Beach": "#0ea5e9", // Sky blue
      "Park": "#10b981", // Emerald
      "Market": "#8b5cf6", // Purple
      "Shopping": "#8b5cf6", // Purple
      "Church": "#64748b", // Slate
      "Castle": "#64748b", // Slate
      "Hiking Trail": "#14b8a6", // Teal
      "Winery": "#db2777", // Pink
      "Local Shop": "#8b5cf6", // Purple
      "Cultural": "#8b5cf6", // Purple
      "Cultural Event": "#d946ef", // Fuchsia
      "Adventure Activity": "#f97316", // Orange
      "Activity": "#f97316", // Orange
      "Wellness": "#06b6d4", // Cyan
      "Other": "#3b82f6", // Blue
    };
    
    return colorMap[category] || colorMap.Other;
  };

  const createInfoWindowContent = (attraction: Attraction): string => {
    return `
      <div class="p-1 max-w-[240px] font-sans">
        <h3 class="font-bold text-base text-gray-900 leading-tight mb-1">${attraction.name}</h3>
        <div class="flex items-center gap-1.5 mb-2">
          <span class="text-[10px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">${attraction.category}</span>
          ${attraction.location ? `<span class="text-[10px] text-gray-500 truncate">${attraction.location}</span>` : ''}
        </div>
        <p class="text-xs text-gray-600 line-clamp-2 leading-relaxed m-0">${attraction.description || ''}</p>
      </div>
    `;
  };

  const handleAddAttractionAtLocation = () => {
    if (!map) return;
    // Open add attraction modal while map context is active.
    onAddNewAttraction();
  };

  const fitMapToAttractions = useCallback(() => {
    if (!map || !google || markers.length === 0) return;

    const bounds = new google.maps.LatLngBounds();
    markers.forEach((marker) => {
      bounds.extend(marker.position);
    });

    map.fitBounds(bounds);

    // Add some padding
    google.maps.event.addListenerOnce(map, "bounds_changed", () => {
      const zoom = map.getZoom();
      if (zoom && zoom > 15) {
        map.setZoom(15);
      }
    });
  }, [map, google, markers]);

  useImperativeHandle(ref, () => ({
    fitToAttractions: fitMapToAttractions,
  }));

  if (!isLoaded) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Loading map...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const mapBody = (
    <div className="relative h-full w-full min-h-[400px]">
      <div ref={mapRef} className="h-full w-full absolute inset-0 focus:outline-none" style={{ minHeight: 'inherit' }} />
            
      {/* Dynamic Category Filter Pills */}
      <div className="absolute left-6 top-6 right-[120px] flex gap-2 overflow-x-auto pb-2 z-10 hide-scrollbar items-center" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
        
        {/* Places Mapped Info & Fit View Button */}
        <div className="flex-shrink-0 flex items-center gap-2 bg-white/95 backdrop-blur-md shadow-md border border-white/60 rounded-full px-4 h-[36px] z-10">
          <span className="text-xs font-semibold text-slate-700">
            <span className="text-blue-600">
              {activeCategoryFilter 
                ? attractions.filter(a => (a.category || a.attraction_type || '') === activeCategoryFilter).length 
                : attractions.length}
            </span> Place(s)
          </span>
          <div className="h-4 w-[1px] bg-slate-200"></div>
          <button
            onClick={fitMapToAttractions}
            disabled={markers.length === 0}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Crosshair className="h-3.5 w-3.5" />
            Fit View
          </button>
        </div>

        <button
          onClick={() => setActiveCategoryFilter(null)}
          className={`flex-shrink-0 px-4 h-[36px] flex items-center rounded-full text-xs font-semibold shadow-md border transition-all duration-300 transform ${
            activeCategoryFilter === null 
              ? 'bg-slate-800 text-white border-slate-800 scale-105' 
              : 'bg-white/95 backdrop-blur-md text-slate-700 border-white/60 hover:bg-white hover:scale-105'
          }`}
        >
          All Places
        </button>
        
        {Array.from(new Set(attractions.map(a => a.category || a.attraction_type || 'Other'))).filter(Boolean).map((cat) => {
          const icon = getMarkerIcon(cat);
          const color = getMarkerColor(cat);
          const isActive = activeCategoryFilter === cat;
          return (
            <button
              key={cat}
              onClick={() => setActiveCategoryFilter(cat)}
              className={`flex-shrink-0 flex items-center gap-1.5 px-4 h-[36px] rounded-full text-xs font-semibold shadow-md border transition-all duration-300 transform ${
                isActive 
                  ? 'text-white scale-105' 
                  : 'bg-white/95 backdrop-blur-md text-slate-700 border-white/60 hover:bg-white hover:scale-105'
              }`}
              style={{
                backgroundColor: isActive ? color : undefined,
                borderColor: isActive ? color : undefined,
              }}
            >
              <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[12px] ${
                isActive ? 'text-white' : 'text-slate-800'
              }`}>
                {icon}
              </span>
              {cat}
            </button>
          );
        })}
      </div>

      {/* Selected Attraction Actions */}
      {selectedMarker && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[90%] max-w-lg rounded-xl bg-white/95 backdrop-blur-md p-4 shadow-xl border border-gray-200/60 flex flex-col gap-3"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                  {selectedMarker.attraction.category || selectedMarker.attraction.attraction_type || "Attraction"}
                </span>
                {selectedMarker.attraction.average_rating != null && (
                  <span className="flex items-center gap-1 text-[10px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-100">
                    ★ {selectedMarker.attraction.average_rating.toFixed(1)} <span className="text-amber-600/70 font-normal">({selectedMarker.attraction.review_count})</span>
                  </span>
                )}
                {selectedMarker.attraction.cost_estimate && (
                  <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                    {selectedMarker.attraction.cost_estimate}
                  </span>
                )}
                {selectedMarker.attraction.authenticity_level && (
                  <span className="text-[10px] font-medium text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-100">
                    {selectedMarker.attraction.authenticity_level} authenticity
                  </span>
                )}
              </div>
              <h4 className="font-semibold text-lg text-gray-900 truncate leading-tight mb-1">
                {selectedMarker.attraction.name}
              </h4>
              {(selectedMarker.attraction.location || selectedMarker.attraction.address) && (
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
                  <MapPin className="h-3 w-3 shrink-0" />
                  <span className="truncate">
                    {selectedMarker.attraction.location || selectedMarker.attraction.address}
                  </span>
                </div>
              )}
            </div>
            <div className="flex flex-col items-end gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="h-8 w-8 p-0 rounded-full hover:bg-gray-100 flex-shrink-0"
                onClick={() => setSelectedMarker(null)}
              >
                <X className="h-4 w-4" />
              </Button>
              {selectedMarker.attraction.featured_image_url || (selectedMarker.attraction.image_gallery && selectedMarker.attraction.image_gallery.length > 0) ? (
                <div className="h-12 w-12 rounded-lg bg-gray-100 overflow-hidden shrink-0 border border-gray-200 shadow-sm">
                  <img src={selectedMarker.attraction.featured_image_url || selectedMarker.attraction.image_gallery?.[0]} alt={selectedMarker.attraction.name} className="h-full w-full object-cover" />
                </div>
              ) : (
                <div className="h-12 w-12 rounded-full bg-sky-50 flex items-center justify-center shrink-0 border border-sky-100">
                  {getCategoryIconComponent(selectedMarker.attraction.category || selectedMarker.attraction.attraction_type, "h-5 w-5 text-sky-600")}
                </div>
              )}
            </div>
          </div>

          {selectedMarker.attraction.description && (
            <p className="text-sm text-gray-600 line-clamp-2 leading-relaxed">
              {selectedMarker.attraction.description}
            </p>
          )}

          {selectedMarker.attraction.host_personal_tip && (
            <div className="text-xs bg-indigo-50/60 p-2 rounded-lg border border-indigo-100 text-indigo-900/90 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-indigo-300"></div>
              <span className="font-semibold text-indigo-700 text-[10px] uppercase tracking-wider block mb-0.5">Host Tip</span>
              <span className="italic line-clamp-2">{`"${selectedMarker.attraction.host_personal_tip}"`}</span>
            </div>
          )}

          <div className="flex items-center gap-2 flex-wrap mt-1">
            <Button
              size="sm"
              variant="primary"
              className="h-7 text-xs shadow-sm"
              onClick={() => onSelectAttraction(selectedMarker.attraction)}
            >
              Edit Details
            </Button>
            
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[10px] text-muted-foreground ml-auto bg-gray-50/50 px-2 py-1 rounded-md border border-gray-100/50">
              {selectedMarker.attraction.duration_hours && (
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3 text-gray-400" />
                  <span>~{selectedMarker.attraction.duration_hours} hr{selectedMarker.attraction.duration_hours !== 1 ? 's' : ''}</span>
                </div>
              )}
              {selectedMarker.attraction.difficulty_level && (
                <div className="flex items-center gap-1">
                  <div className={`h-1.5 w-1.5 rounded-full ${
                    selectedMarker.attraction.difficulty_level === 'easy' ? 'bg-green-400' :
                    selectedMarker.attraction.difficulty_level === 'moderate' ? 'bg-yellow-400' :
                    'bg-red-400'
                  }`} />
                  <span className="capitalize">{selectedMarker.attraction.difficulty_level}</span>
                </div>
              )}
              {selectedMarker.attraction.contact_info?.phone && (
                <div className="flex items-center gap-1">
                  <Phone className="h-3 w-3 text-gray-400" />
                  <span>{selectedMarker.attraction.contact_info.phone}</span>
                </div>
              )}
              {selectedMarker.attraction.contact_info?.website && (
                <a 
                  href={selectedMarker.attraction.contact_info.website} 
                  target="_blank" 
                  rel="noreferrer"
                  className="flex items-center gap-1 hover:text-blue-600 transition-colors text-blue-500 font-medium"
                >
                  <Globe className="h-3 w-3" />
                  <span>Site</span>
                </a>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );

  if (embedded) {
    return <div className={`h-full w-full ${className || ''}`}>{mapBody}</div>;
  }

  return (
    <div className={className}>
      <Card>
        {!hideTitle && (
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Attractions Map</CardTitle>
                <p className="text-sm text-gray-600">
                  {attractions.length} attractions • Click markers for details
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={fitMapToAttractions}
                  disabled={markers.length === 0}
                >
                  <Crosshair className="mr-1.5 h-3.5 w-3.5" />
                  Fit to Attractions
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleAddAttractionAtLocation}
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  Add at Location
                </Button>
              </div>
            </div>
          </CardHeader>
        )}
        <CardContent>{mapBody}</CardContent>
      </Card>
    </div>
  );
});

HostMapView.displayName = "HostMapView";
