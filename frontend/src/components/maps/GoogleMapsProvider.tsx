"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { Loader } from "@googlemaps/js-api-loader";

interface GoogleMapsContextType {
  isLoaded: boolean;
  google: typeof window.google | null;
  map: google.maps.Map | null;
  setMap: (map: google.maps.Map | null) => void;
  mapId: string | undefined;
}

const GoogleMapsContext = createContext<GoogleMapsContextType | undefined>(undefined);

export const useGoogleMaps = () => {
  const context = useContext(GoogleMapsContext);
  if (context === undefined) {
    throw new Error("useGoogleMaps must be used within a GoogleMapsProvider");
  }
  return context;
};

interface GoogleMapsProviderProps {
  children: ReactNode;
  apiKey: string;
  mapId?: string; // Optional Map ID for Advanced Markers
}

export const GoogleMapsProvider: React.FC<GoogleMapsProviderProps> = ({ 
  children, 
  apiKey,
  mapId
}) => {
  // Use provided Map ID or default to DEMO_MAP_ID for Advanced Markers
  const effectiveMapId = mapId || "DEMO_MAP_ID";
  const [isLoaded, setIsLoaded] = useState(false);
  const [mapsApi, setMapsApi] = useState<typeof window.google | null>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);

  useEffect(() => {
    const loader = new Loader({
      apiKey: apiKey,
      version: "weekly",
      libraries: ["places", "geometry", "marker"]
    });

    loader.load().then(() => {
      setMapsApi(window.google);
      setIsLoaded(true);
    }).catch((error) => {
      console.error("Error loading Google Maps API:", error);
    });
  }, [apiKey]);

  const contextValue: GoogleMapsContextType = {
    isLoaded,
    google: mapsApi,
    map,
    setMap,
    mapId: effectiveMapId
  };

  return (
    <GoogleMapsContext.Provider value={contextValue}>
      {children}
    </GoogleMapsContext.Provider>
  );
};
