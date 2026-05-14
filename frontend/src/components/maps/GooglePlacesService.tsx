"use client";

import React, { useEffect, useState } from "react";
import { useGoogleMaps } from "./GoogleMapsProvider";

interface PlaceDetails {
  place_id: string;
  name: string;
  formatted_address: string;
  rating?: number;
  user_ratings_total?: number;
  photos?: Array<{
    photo_reference: string;
    height: number;
    width: number;
  }>;
  opening_hours?: {
    weekday_text?: string[];
  };
  website?: string;
  phone_number?: string;
  price_level?: number;
  types?: string[];
  geometry: {
    location: {
      lat: number;
      lng: number;
    };
  };
}

interface GooglePlacesServiceProps {
  query: string;
  location?: { lat: number; lng: number };
  radius?: number;
  onPlacesFound?: (places: PlaceDetails[]) => void;
  onError?: (error: string) => void;
}

export const GooglePlacesService: React.FC<GooglePlacesServiceProps> = ({
  query,
  location,
  radius = 5000,
  onPlacesFound,
  onError
}) => {
  const { isLoaded, google } = useGoogleMaps();
  const [isSearching, setIsSearching] = useState(false);

  // Search places when query changes
  useEffect(() => {
    if (!isLoaded || !google || !query.trim()) return;

    const searchPlaces = async () => {
      setIsSearching(true);

      try {
        // Use the new Place class instead of deprecated PlacesService
        const { Place } = (await google.maps.importLibrary("places")) as unknown as {
          Place: {
            searchByText: (req: Record<string, unknown>) => Promise<unknown[] | { places?: unknown[] }>;
          };
        };

        const searchRequest = {
          textQuery: query,
          ...(location && {
            locationBias: {
              center: { lat: location.lat, lng: location.lng },
              radius: radius
            }
          })
        };

        const rawPlaces = await Place.searchByText(searchRequest);
        const pAny = rawPlaces as unknown[] | { places?: unknown[] } | null | undefined;
        const places = Array.isArray(pAny)
          ? pAny
          : pAny && typeof pAny === "object" && Array.isArray((pAny as { places: unknown[] }).places)
            ? (pAny as { places: unknown[] }).places
            : [];

        setIsSearching(false);

        if (places.length > 0) {
          const placeDetails: PlaceDetails[] = places.map((place) => {
            const p = place as Record<string, unknown>;
            const opening = p.openingHours as { weekdayText?: string[] } | undefined;
            return {
            place_id: String(p.id ?? ""),
            name: String(p.displayName ?? ""),
            formatted_address: String(p.formattedAddress ?? ""),
            rating: p.rating as number | undefined,
            user_ratings_total: p.userRatingCount as number | undefined,
            photos: p.photos as PlaceDetails["photos"],
            opening_hours: opening
              ? { weekday_text: opening.weekdayText }
              : undefined,
            website: p.website as string | undefined,
            phone_number: p.formattedPhoneNumber as string | undefined,
            price_level: p.priceLevel as number | undefined,
            types: (p.types as string[]) || [],
            geometry: {
              location: p.location as { lat: number; lng: number }
            }
          };
          });

          if (onPlacesFound) {
            onPlacesFound(placeDetails);
          }
        } else {
          const errorMessage = "No places found";
          console.error(errorMessage);
          if (onError) {
            onError(errorMessage);
          }
        }
      } catch (error) {
        setIsSearching(false);
        const errorMessage = `Places search failed: ${error}`;
        console.error(errorMessage);
        if (onError) {
          onError(errorMessage);
        }
      }
    };

    searchPlaces();
  }, [isLoaded, google, query, location, radius, onPlacesFound, onError]);

  return null; // This component doesn't render anything
};

// Hook for getting place details
export const usePlaceDetails = (placeId: string | null) => {
  const { isLoaded, google } = useGoogleMaps();
  const [placeDetails, setPlaceDetails] = useState<PlaceDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || !google || !placeId) {
      setPlaceDetails(null);
      return;
    }

    const getPlaceDetails = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Use the new Place class instead of deprecated PlacesService
        const { Place } = (await google.maps.importLibrary("places")) as unknown as {
          Place: new (opts: { id: string }) => {
            fetchFields: (opts: { fields: string[] }) => Promise<void>;
            id: string;
            displayName?: string;
            formattedAddress?: string;
            rating?: number;
            userRatingCount?: number;
            photos?: PlaceDetails["photos"];
            openingHours?: { weekdayText?: string[] };
            website?: string;
            formattedPhoneNumber?: string;
            priceLevel?: number;
            types?: string[];
            location: { lat: number; lng: number };
          };
        };

        const place = new Place({ id: placeId });
        
        await place.fetchFields({
          fields: [
            'displayName',
            'formattedAddress',
            'rating',
            'userRatingCount',
            'photos',
            'openingHours',
            'website',
            'formattedPhoneNumber',
            'priceLevel',
            'types',
            'location'
          ]
        });

        const placeDetailsData: PlaceDetails = {
          place_id: place.id ?? "",
          name: place.displayName ?? "",
          formatted_address: place.formattedAddress ?? "",
          rating: place.rating,
          user_ratings_total: place.userRatingCount,
          photos: place.photos,
          opening_hours: place.openingHours ? {
            weekday_text: place.openingHours.weekdayText
          } : undefined,
          website: place.website,
          phone_number: place.formattedPhoneNumber,
          price_level: place.priceLevel,
          types: place.types || [],
          geometry: {
            location: place.location
          }
        };
        
        setPlaceDetails(placeDetailsData);
      } catch (error) {
        const errorMessage = `Failed to get place details: ${error}`;
        setError(errorMessage);
        console.error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    getPlaceDetails();
  }, [isLoaded, google, placeId]);

  return { placeDetails, isLoading, error };
};

// Hook for nearby search
export const useNearbySearch = (
  location: { lat: number; lng: number } | null,
  radius: number = 5000,
  types: string[] = []
) => {
  const { isLoaded, google } = useGoogleMaps();
  const [places, setPlaces] = useState<PlaceDetails[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || !google || !location) {
      setPlaces([]);
      return;
    }

    const searchNearby = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Use the new Place class instead of deprecated PlacesService
        const { Place } = (await google.maps.importLibrary("places")) as unknown as {
          Place: {
            searchNearby: (req: Record<string, unknown>) => Promise<unknown[] | { places?: unknown[] } | null | undefined>;
          };
        };

        const request = {
          locationRestriction: {
            center: { lat: location.lat, lng: location.lng },
            radius: radius
          },
          ...(types.length > 0 && { typesFilter: types })
        };

        const nearbyRaw = await Place.searchNearby(request);
        const nearbyPlaces = Array.isArray(nearbyRaw)
          ? nearbyRaw
          : nearbyRaw && typeof nearbyRaw === "object" && Array.isArray((nearbyRaw as { places: unknown[] }).places)
            ? (nearbyRaw as { places: unknown[] }).places
            : [];

        setIsLoading(false);

        if (nearbyPlaces.length > 0) {
          const placesData: PlaceDetails[] = nearbyPlaces.map((place) => {
            const p = place as Record<string, unknown>;
            const opening = p.openingHours as { weekdayText?: string[] } | undefined;
            return {
            place_id: String(p.id ?? ""),
            name: String(p.displayName ?? ""),
            formatted_address: String(p.formattedAddress ?? ""),
            rating: p.rating as number | undefined,
            user_ratings_total: p.userRatingCount as number | undefined,
            photos: p.photos as PlaceDetails["photos"],
            opening_hours: opening
              ? { weekday_text: opening.weekdayText }
              : undefined,
            website: p.website as string | undefined,
            phone_number: p.formattedPhoneNumber as string | undefined,
            price_level: p.priceLevel as number | undefined,
            types: (p.types as string[]) || [],
            geometry: {
              location: p.location as { lat: number; lng: number }
            }
          };
          });
          setPlaces(placesData);
        } else {
          setPlaces([]);
        }
      } catch (error) {
        setIsLoading(false);
        const errorMessage = `Nearby search failed: ${error}`;
        setError(errorMessage);
        console.error(errorMessage);
      }
    };

    searchNearby();
  }, [isLoaded, google, location, radius, types]);

  return { places, isLoading, error };
};
