"use client";

import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useGoogleMaps } from "./GoogleMapsProvider";
import { Attraction, API_BASE_URL } from "@/lib/api";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";
import { Check } from "lucide-react";

// TypeScript declarations for Google GenAI SDK
declare global {
  interface Window {
    google?: {
      genai?: {
        GoogleGenAI: any;
      };
    };
  }
}

/**
 * Enhanced Place interface with comprehensive Google Places data
 */
export interface EnhancedPlace {
  place_id: string;
  name: string;
  displayName?: string;
  formatted_address: string;
  types: string[];
  rating?: number;
  user_ratings_total?: number;
  price_level?: number;
  photos?: Array<{
    photo_reference: string;
    height: number;
    width: number;
  }>;
  geometry: {
    location: {
      lat: number | (() => number);
      lng: number | (() => number);
    };
  };
  website?: string;
  phone_number?: string;
  opening_hours?: {
    weekday_text?: string[];
  };
  editorial_summary?: string;
}

/**
 * Props for the Google Map Preview component
 */
interface GoogleMapPreviewProps {
  latitude: number;
  longitude: number;
  address: string;
  google: typeof google;
  mapId: string;
  onLocationAdjust?: (lat: number, lng: number) => void;
}

/**
 * Props for the main Enhanced Attraction Modal
 */
interface EnhancedAttractionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: Partial<Attraction>) => void;
  data: Partial<Attraction>;
  onChange: (data: Partial<Attraction>) => void;
  mode: 'create' | 'edit';
  selectedPlace?: EnhancedPlace | null;
}

// ============================================================================
// CONSTANTS & UTILITIES
// ============================================================================

/**
 * Available attraction types for categorization
 */
const ATTRACTION_TYPES = [
  'historic',
  'natural',
  'cultural',
  'culinary',
  'activity',
  'seasonal',
  'accommodation',
  'shopping',
  'nightlife',
  'family',
  'romantic',
  'hidden_gem'
] as const;

/**
 * Mapping from Google Places types to attraction categories
 */
const PLACE_TYPE_TO_CATEGORY_MAP: Record<string, string> = {
  'restaurant': 'culinary',
  'food': 'culinary',
  'cafe': 'culinary',
  'bar': 'culinary',
  'museum': 'cultural',
  'art_gallery': 'cultural',
  'church': 'historic',
  'place_of_worship': 'historic',
  'castle': 'historic',
  'historic': 'historic',
  'tourist_attraction': 'cultural',
  'park': 'natural',
  'natural_feature': 'natural',
  'beach': 'natural',
  'amusement_park': 'activity',
  'aquarium': 'cultural',
  'zoo': 'natural',
  'shopping_mall': 'shopping',
  'store': 'shopping',
  'market': 'shopping',
  'winery': 'culinary',
  'spa': 'wellness',
  'gym': 'activity',
  'hiking': 'activity',
  'campground': 'activity',
  'hotel': 'accommodation',
  'lodging': 'accommodation',
  'night_club': 'nightlife',
  'entertainment': 'activity'
};

/**
 * Price level text mapping
 */
const PRICE_LEVEL_TEXT: Record<number, string> = {
  0: 'Free',
  1: 'Inexpensive',
  2: 'Moderate',
  3: 'Expensive',
  4: 'Very Expensive'
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Maps Google Places types to attraction categories
 */
const getCategoryFromTypes = (types: string[]): string => {
  for (const type of types) {
    if (PLACE_TYPE_TO_CATEGORY_MAP[type]) {
      return PLACE_TYPE_TO_CATEGORY_MAP[type];
    }
  }
  return 'cultural'; // Default fallback
};

/**
 * Gets human-readable price level text
 */
const getPriceLevelText = (priceLevel: number): string => {
  return PRICE_LEVEL_TEXT[priceLevel] || 'Price not specified';
};

// ============================================================================
// GOOGLE MAP PREVIEW COMPONENT
// ============================================================================

/**
 * Google Map Preview Component
 * Displays an interactive map with location selection capabilities
 */
const GoogleMapPreview: React.FC<GoogleMapPreviewProps> = ({
  latitude,
  longitude,
  address,
  google,
  mapId,
  onLocationAdjust
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<google.maps.Map | null>(null);
  const marker = useRef<google.maps.Marker | google.maps.marker.AdvancedMarkerElement | null>(null);

  useEffect(() => {
    if (!mapRef.current || !google || !latitude || !longitude) return;

    const initializeMap = async () => {
      try {
        const { AdvancedMarkerElement } = (await google.maps.importLibrary("marker")) as unknown as {
          AdvancedMarkerElement: new (opts: {
            map: google.maps.Map;
            position: google.maps.LatLngLiteral;
            title?: string;
          }) => google.maps.marker.AdvancedMarkerElement;
        };

        const position = { lat: latitude, lng: longitude };

        // Create map instance with Map ID for Advanced Markers
        const mapOptions: google.maps.MapOptions = {
          center: position,
          zoom: 15,
          mapTypeId: google.maps.MapTypeId.ROADMAP,
          disableDefaultUI: true,
          zoomControl: true,
          streetViewControl: false,
          mapTypeControl: false,
          fullscreenControl: false,
          mapId: mapId || "DEMO_MAP_ID",
          styles: [
            {
              featureType: "poi",
              elementType: "labels",
              stylers: [{ visibility: "off" }]
            }
          ]
        };

        if (!mapRef.current) return;
        mapInstance.current = new google.maps.Map(mapRef.current, mapOptions);

        // Add advanced marker
        marker.current = new AdvancedMarkerElement({
          map: mapInstance.current,
          position: position,
          title: address,
        });

        // Add info window
        const infoWindow = new google.maps.InfoWindow({
          content: `<div style="padding: 8px; font-size: 14px;"><strong>${address}</strong></div>`
        });

        // Add click listener to marker
        if (marker.current) {
          marker.current.addListener("click", () => {
            infoWindow.open(mapInstance.current, marker.current);
          });
        }

        // Add map click listener for location adjustment
        if (onLocationAdjust) {
          mapInstance.current.addListener("click", (event: google.maps.MapMouseEvent) => {
            if (event.latLng) {
              const newLat = event.latLng.lat();
              const newLng = event.latLng.lng();

              // Update marker position
              if (marker.current && 'position' in marker.current) {
                (marker.current as any).position = { lat: newLat, lng: newLng };
              }

              // Call the adjustment callback
              onLocationAdjust(newLat, newLng);

              // Update info window
              infoWindow.setContent(`<div style="padding: 8px; font-size: 14px;"><strong>Adjusted Location</strong><br>${newLat.toFixed(6)}, ${newLng.toFixed(6)}</div>`);
              infoWindow.open(mapInstance.current, marker.current);
            }
          });
        }

        // Auto-open info window
        setTimeout(() => {
          infoWindow.open(mapInstance.current, marker.current);
        }, 1000);

      } catch (error) {
        console.error('Error initializing map with AdvancedMarkerElement:', error);
        initializeFallbackMap();
      }
    };

    const initializeFallbackMap = () => {
      try {
        const position = { lat: latitude, lng: longitude };

        const fallbackMapOptions: google.maps.MapOptions = {
          center: position,
          zoom: 15,
          mapTypeId: google.maps.MapTypeId.ROADMAP,
          disableDefaultUI: true,
          zoomControl: true,
          streetViewControl: false,
          mapTypeControl: false,
          fullscreenControl: false,
          mapId: mapId || "DEMO_MAP_ID"
        };

        if (!mapRef.current) return;
        mapInstance.current = new google.maps.Map(mapRef.current, fallbackMapOptions);

        marker.current = new google.maps.Marker({
          position: position,
          map: mapInstance.current,
          title: address,
          animation: google.maps.Animation.DROP,
          draggable: !!onLocationAdjust,
        });

        const infoWindow = new google.maps.InfoWindow({
          content: `<div style="padding: 8px; font-size: 14px;"><strong>${address}</strong></div>`,
        });

        const fallbackMarker = marker.current as google.maps.Marker;
        fallbackMarker.addListener("click", () => {
          infoWindow.open(mapInstance.current, fallbackMarker);
        });

        if (onLocationAdjust) {
          fallbackMarker.addListener("dragend", () => {
            const newPosition = fallbackMarker.getPosition();
            if (newPosition) {
              onLocationAdjust(newPosition.lat(), newPosition.lng());
            }
          });
        }

        setTimeout(() => {
          infoWindow.open(mapInstance.current, fallbackMarker);
        }, 1000);
      } catch (fallbackError) {
        console.error('Fallback marker also failed:', fallbackError);
      }
    };

    initializeMap();

    return () => {
      if (marker.current) {
        try {
          google.maps.event.clearInstanceListeners(marker.current);
        } catch (error) {
          console.error('Error clearing marker listeners:', error);
        }
      }
    };
  }, [latitude, longitude, address, google, onLocationAdjust, mapId]);

  return (
    <div
      ref={mapRef}
      className="w-full h-full rounded-lg"
      style={{ minHeight: '200px' }}
    />
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

/**
 * Enhanced Attraction Modal Component
 * Provides a comprehensive interface for creating and editing attractions
 * with Google Places integration for location search and data enrichment
 */
export const EnhancedAttractionModal: React.FC<EnhancedAttractionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  data,
  onChange,
  mode,
  selectedPlace
}) => {
  // ============================================================================
  // HOOKS & STATE
  // ============================================================================

  const { isLoaded, google, mapId } = useGoogleMaps();
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Content generation state
  const [isGeneratingContent, setIsGeneratingContent] = useState(false);
  const [aiGenerationStatus, setAiGenerationStatus] = useState<string>('');
  const [isGeneratingDescription, setIsGeneratingDescription] = useState(false);

  // Location search state
  const [locationSearchQuery, setLocationSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<EnhancedPlace[]>([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [isSearchingLocation, setIsSearchingLocation] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState<EnhancedPlace | null>(null);

  // Nearby places state
  const [nearbyPlaces, setNearbyPlaces] = useState<EnhancedPlace[]>([]);
  const [isEditingDescription, setIsEditingDescription] = useState(false);
  const [showRawMarkdown, setShowRawMarkdown] = useState(false);

  // Load Google GenAI SDK
  useEffect(() => {
    const loadGeminiSDK = async () => {
      if (typeof window !== 'undefined' && !window.google?.genai) {
        try {
          // Load the Google GenAI SDK
          const script = document.createElement('script');
          script.src = 'https://unpkg.com/@google/generative-ai@latest/dist/web/index.js';
          script.async = true;
          script.onload = () => {
            console.log('Google GenAI SDK loaded successfully');
          };
          script.onerror = () => {
            console.log('Google GenAI SDK failed to load, will use backend API fallback');
          };
          document.head.appendChild(script);
        } catch (error) {
          console.log('Error loading Google GenAI SDK:', error);
        }
      }
    };

    loadGeminiSDK();
  }, []);

  // Load Google GenAI SDK
  useEffect(() => {
    const loadGeminiSDK = async () => {
      if (typeof window !== 'undefined' && !window.google?.genai) {
        try {
          // Load the Google GenAI SDK
          const script = document.createElement('script');
          script.src = 'https://unpkg.com/@google/generative-ai@latest/dist/web/index.js';
          script.async = true;
          script.onload = () => {
            console.log('Google GenAI SDK loaded successfully');
          };
          script.onerror = () => {
            console.log('Google GenAI SDK failed to load, will use backend API fallback');
          };
          document.head.appendChild(script);
        } catch (error) {
          console.log('Error loading Google GenAI SDK:', error);
        }
      }
    };

    loadGeminiSDK();
  }, []);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Pre-fill data from selected place
  useEffect(() => {
    if (selectedPlace && mode === 'create') {
      handlePlaceSelection(selectedPlace);
    }
  }, [selectedPlace, mode]);

  // ============================================================================
  // LOCATION SEARCH FUNCTIONS
  // ============================================================================

  /**
   * Searches for places using Google Places API with multiple fallback strategies
   */
  const searchPlaces = async (query: string) => {
    if (!google || !query.trim()) return;

    setIsSearchingLocation(true);
    setSearchResults([]);

    // Initialize places variable
    let places: any[] = [];

    try {
      // Method 1: Try new Places API
      try {
        const { Place } = (await google.maps.importLibrary("places")) as unknown as {
          Place: { searchByText: (req: Record<string, unknown>) => Promise<unknown> };
        };

        const request = {
          textQuery: query,
          fields: ['id', 'displayName', 'formattedAddress', 'types', 'rating', 'userRatingCount', 'priceLevel', 'photos', 'location', 'websiteURI', 'nationalPhoneNumber', 'regularOpeningHours', 'editorialSummary'],
          maxResultCount: 10
        };

        const rawSearchResults = await Place.searchByText(request);
        const rawAny = rawSearchResults as unknown[] | { places?: unknown[] } | null | undefined;
        const searchResults = Array.isArray(rawAny)
          ? rawAny
          : rawAny && typeof rawAny === "object" && Array.isArray((rawAny as { places: unknown[] }).places)
            ? (rawAny as { places: unknown[] }).places
            : [];

        if (searchResults && searchResults.length > 0) {
          places = searchResults.map((place: any) => ({
            place_id: place.id || `new_${Date.now()}_${Math.random()}`,
            name: place.displayName || 'Unknown Place',
            displayName: place.displayName || 'Unknown Place',
            formatted_address: place.formattedAddress || 'Address not available',
            types: place.types || [],
            rating: place.rating,
            user_ratings_total: place.userRatingCount,
            price_level: place.priceLevel,
            photos: place.photos || [],
            geometry: {
              location: {
                lat: typeof place.location?.lat === 'function' ? place.location.lat() : place.location?.lat || 0,
                lng: typeof place.location?.lng === 'function' ? place.location.lng() : place.location?.lng || 0
              }
            },
            website: place.websiteURI || place.website,
            phone_number: place.nationalPhoneNumber || place.formatted_phone_number,
            opening_hours: place.regularOpeningHours ? {
              weekday_text: place.regularOpeningHours.weekdayText
            } : place.opening_hours ? {
              weekday_text: place.opening_hours.weekday_text
            } : undefined,
            editorial_summary: place.editorialSummary || place.editorial_summary
          }));
        }
      } catch (error) {
        console.log('New Places API search failed:', error);
      }

      // Method 3: Alternative search strategies
      if (places.length === 0) {
        console.log('Trying alternative search strategies...');

        // Try with different query variations
        const alternativeQueries = [
          `${query} Croatia`,
          `${query} Istria`,
          `${query} Kvarner`,
          query.replace(/\s+/g, '+')
        ];

        for (const altQuery of alternativeQueries) {
          if (places.length > 0) break;

          try {
            const { Place } = (await google.maps.importLibrary("places")) as unknown as {
              Place: { searchByText: (req: Record<string, unknown>) => Promise<unknown> };
            };

            const request = {
              textQuery: altQuery,
              fields: ['id', 'displayName', 'formattedAddress', 'types', 'rating', 'userRatingCount', 'priceLevel', 'photos', 'location', 'editorialSummary', 'websiteURI', 'nationalPhoneNumber', 'regularOpeningHours'],
              maxResultCount: 5
            };

            const rawAltResults = await Place.searchByText(request);
            const altAny = rawAltResults as unknown[] | { places?: unknown[] } | null | undefined;
            const altResults = Array.isArray(altAny)
              ? altAny
              : altAny && typeof altAny === "object" && Array.isArray((altAny as { places: unknown[] }).places)
                ? (altAny as { places: unknown[] }).places
                : [];
            if (altResults && altResults.length > 0) {
              places = altResults.map((place: any) => ({
                place_id: place.id || `alt_${Date.now()}_${Math.random()}`,
                name: place.displayName || 'Alternative Result',
                displayName: place.displayName || 'Alternative Result',
                formatted_address: place.formattedAddress || 'Address not available',
                types: place.types || [],
                rating: place.rating,
                user_ratings_total: place.userRatingCount,
                price_level: place.priceLevel,
                photos: place.photos || [],
                geometry: {
                  location: {
                    lat: typeof place.location?.lat === 'function' ? place.location.lat() : place.location?.lat || 0,
                    lng: typeof place.location?.lng === 'function' ? place.location.lng() : place.location?.lng || 0
                  }
                }
              }));
            }
          } catch (error) {
            console.log(`Alternative query "${altQuery}" failed:`, error);
          }
        }
      }

      // Process and display results
      if (places.length > 0) {
        const allResults = places.map((place: any) => {
          const mappedPlace: EnhancedPlace = {
            place_id: place.place_id || `mapped_${Date.now()}_${Math.random()}`,
            name: place.name || 'Mapped Place',
            displayName: place.displayName || place.name || 'Mapped Place',
            formatted_address: place.formatted_address || 'Address not available',
            types: place.types || [],
            rating: place.rating,
            user_ratings_total: place.user_ratings_total,
            price_level: place.price_level,
            photos: place.photos || [],
            geometry: {
              location: {
                lat: typeof place.geometry?.location?.lat === 'function' ? place.geometry.location.lat() : (place.geometry?.location?.lat || 0),
                lng: typeof place.geometry?.location?.lng === 'function' ? place.geometry.location.lng() : (place.geometry?.location?.lng || 0)
              }
            },
            website: place.websiteURI || place.website,
            phone_number: place.nationalPhoneNumber || place.formatted_phone_number,
            opening_hours: place.regularOpeningHours ? {
              weekday_text: place.regularOpeningHours.weekdayText
            } : place.opening_hours ? {
              weekday_text: place.opening_hours.weekday_text
            } : undefined,
            editorial_summary: place.editorialSummary || place.editorial_summary
          };

          return mappedPlace;
        });

        // Remove duplicates and limit results
        const uniqueResults = allResults.filter((place, index, self) =>
          index === self.findIndex(p => p.place_id === place.place_id)
        ).slice(0, 10);

        console.log('🎯 Total results found:', allResults.length);
        console.log('🎯 Unique results after deduplication:', uniqueResults.length);

        setSearchResults(uniqueResults);
        setShowSearchDropdown(uniqueResults.length > 0);

        if (uniqueResults.length === 0) {
          const message = `🔍 No places found for "${query}". Try a different search term or be more specific.`;
          console.log(message);
          setAiGenerationStatus(message);
          setTimeout(() => setAiGenerationStatus(''), 5000);
        } else {
          console.log('✅ Search completed successfully with results');
        }
      } else {
        console.log('❌ No places found in any search method');
        setAiGenerationStatus(`🔍 No places found for "${query}". Try a different search term or be more specific.`);
        setTimeout(() => setAiGenerationStatus(''), 5000);
      }
    } catch (error) {
      console.error('❌ Error in searchPlaces:', error);
      setAiGenerationStatus(`❌ Search error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setTimeout(() => setAiGenerationStatus(''), 5000);
    } finally {
      setIsSearchingLocation(false);
    }
  };

  /**
   * Gets nearby places for the selected location using Google Places API
   */
  const getNearbyPlaces = async (location: google.maps.LatLng) => {
    if (!google || !location) return;

    try {
      const { Place } = (await google.maps.importLibrary("places")) as unknown as {
        Place: {
          searchNearby: (req: Record<string, unknown>) => Promise<unknown[] | { places?: unknown[] } | null | undefined>;
        };
      };

      // Ensure location is a valid LatLng object
      if (!(location instanceof google.maps.LatLng)) {
        console.error('Invalid location object for nearby places search');
        return;
      }

      const request = {
        fields: ['id', 'displayName', 'formattedAddress', 'types', 'rating', 'userRatingCount', 'priceLevel', 'photos', 'location', 'editorialSummary'],
        locationRestriction: {
          center: location,
          radius: 5000
        },
        includedPrimaryTypes: ['restaurant', 'cafe', 'bar', 'tourist_attraction', 'museum', 'park'],
        maxResultCount: 5
      };

      const nearbyRaw = await Place.searchNearby(request);
      const nearbyList: unknown[] = Array.isArray(nearbyRaw)
        ? nearbyRaw
        : nearbyRaw && typeof nearbyRaw === "object" && Array.isArray((nearbyRaw as { places: unknown[] }).places)
          ? (nearbyRaw as { places: unknown[] }).places
          : [];

      if (nearbyList.length > 0) {
        const mappedNearby: EnhancedPlace[] = nearbyList.slice(0, 5).map((place: any) => ({
          place_id: place.id || `nearby_${Date.now()}_${Math.random()}`,
          name: place.displayName || 'Nearby Place',
          displayName: place.displayName || 'Nearby Place',
          formatted_address: place.formattedAddress || 'Address not available',
          types: place.types || [],
          rating: place.rating,
          user_ratings_total: place.userRatingCount,
          price_level: place.priceLevel,
          photos: place.photos || [],
          geometry: {
            location: {
              lat: typeof place.location?.lat === 'function' ? place.location.lat() : place.location?.lat || 0,
              lng: typeof place.location?.lng === 'function' ? place.location.lng() : place.location?.lng || 0
            }
          }
        }));

        setNearbyPlaces(mappedNearby);
      }
    } catch (error) {
      console.error('Error getting nearby places:', error);
    }
  };

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  /**
   * Handles location input changes with debounced search
   */
  const handleLocationInputChange = (value: string) => {
    setLocationSearchQuery(value);
    setShowSearchDropdown(false);
    setSearchResults([]);

    // Clear existing timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Debounce search
    if (value.trim().length >= 3) {
      searchTimeoutRef.current = setTimeout(() => {
        searchPlaces(value.trim());
      }, 500);
    }
  };

  /**
   * Handles place selection with auto-population
   */
  const handlePlaceSelection = (place: EnhancedPlace) => {
    setSelectedLocation(place);
    setLocationSearchQuery(place.displayName || place.name);
    setShowSearchDropdown(false);
    setSearchResults([]);

    // Extract city from address
    const addressParts = place.formatted_address.split(',');
    const city = addressParts[0]?.trim() || '';

    // Extract a photo if available
    let featured_image_url = null;
    const image_gallery: string[] = [];
    if (place.photos && place.photos.length > 0) {
      try {
        const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';
        const getPhotoUrl = (photo: any) => {
          if (typeof photo.getURI === 'function') {
            return photo.getURI({ maxWidth: 800 });
          } else if (typeof photo.getUrl === 'function') {
            return photo.getUrl({ maxWidth: 800 });
          } else if (photo.photoURI) {
            return photo.photoURI;
          } else if (photo.photo_reference && apiKey) {
            return `https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference=${photo.photo_reference}&key=${apiKey}`;
          }
          return null;
        };

        const firstPhoto = getPhotoUrl(place.photos[0]);
        if (firstPhoto) {
          featured_image_url = firstPhoto;
          for (let i = 0; i < Math.min(place.photos.length, 5); i++) {
            const url = getPhotoUrl(place.photos[i]);
            if (url) image_gallery.push(url);
          }
        }
      } catch (err) {
        console.error("Error extracting Google Place photos:", err);
      }
    }

    // Auto-populate all available fields
    onChange({
      ...data,
      name: place.displayName || place.name,
      city: city,
      address: place.formatted_address,
      location: place.formatted_address,
      attraction_type: getCategoryFromTypes(place.types),
      description: place.editorial_summary || '',
      admission_fee: place.price_level ? getPriceLevelText(place.price_level) : '',
      difficulty_level: 'easy',
      latitude: typeof place.geometry?.location?.lat === 'function' ? place.geometry.location.lat() : (place.geometry?.location?.lat ?? null),
      longitude: typeof place.geometry?.location?.lng === 'function' ? place.geometry.location.lng() : (place.geometry?.location?.lng ?? null),
      category_tags: place.types || [],
      host_personal_tip: '',
      host_favorite_time: '',
      host_insider_info: '',
      google_place_id: place.place_id || '',
      featured_image_url: featured_image_url,
      image_gallery: image_gallery.length > 0 ? image_gallery : data.image_gallery
    });

    const lat = typeof place.geometry?.location?.lat === 'function' ? place.geometry.location.lat() : place.geometry?.location?.lat;
    const lng = typeof place.geometry?.location?.lng === 'function' ? place.geometry.location.lng() : place.geometry?.location?.lng;

    // Get nearby places for AI enhancement
    if (lat && lng && google) {
      const latLng = new google.maps.LatLng(lat, lng);
      getNearbyPlaces(latLng);
    }

    // Show success message
    setAiGenerationStatus(`✅ Found: ${place.displayName || place.name} - Auto-populated with Google Places data!`);
    setTimeout(() => setAiGenerationStatus(''), 3000);
  };

  /**
   * Handles location adjustment from map clicks
   */
  const handleLocationAdjust = (lat: number, lng: number) => {
    // Update the selected location with new coordinates
    if (selectedLocation) {
      setSelectedLocation({
        ...selectedLocation,
        geometry: {
          ...selectedLocation.geometry,
          location: { lat, lng }
        }
      });
    }

    // Update the form data
    onChange({
      ...data,
      latitude: lat,
      longitude: lng
    });

    // Show adjustment confirmation
    setAiGenerationStatus(`📍 Location adjusted to: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
    setTimeout(() => setAiGenerationStatus(''), 3000);
  };

  const resolveCoordinatesBeforeSubmit = async (): Promise<{ lat: number; lng: number } | null> => {
    if (typeof data.latitude === 'number' && typeof data.longitude === 'number') {
      return { lat: data.latitude, lng: data.longitude };
    }

    if (!google) {
      return null;
    }

    const query = [data.address, data.city].filter(Boolean).join(', ').trim();
    if (!query) {
      return null;
    }

    return new Promise((resolve) => {
      const geocoder = new google.maps.Geocoder();
      geocoder.geocode({ address: query }, (results, status) => {
        if (status === google.maps.GeocoderStatus.OK && results?.[0]) {
          const location = results[0].geometry.location;
          resolve({ lat: location.lat(), lng: location.lng() });
          return;
        }
        resolve(null);
      });
    });
  };

  /**
   * Handles form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!data.name || !data.address || !data.city) {
      setAiGenerationStatus('❌ Please fill in at least name, address and city');
      setTimeout(() => setAiGenerationStatus(''), 3000);
      return;
    }

    const coordinates = await resolveCoordinatesBeforeSubmit();
    if (!coordinates) {
      setAiGenerationStatus('❌ Unable to resolve geolocation. Please pick a Place result or adjust address/city.');
      setTimeout(() => setAiGenerationStatus(''), 5000);
      return;
    }

    const payload = {
      ...data,
      latitude: coordinates.lat,
      longitude: coordinates.lng,
    };
    onChange(payload);
    onSubmit(payload);
    onClose();
  };

  /**
 * Generates AI-enhanced description using Google GenAI SDK or backend API fallback
 */
  const generateAIDescription = async () => {
    // In edit mode, we can use existing attraction data
    // In create mode, we need selectedLocation
    if (mode === 'create' && (!selectedLocation || !selectedLocation.geometry?.location)) {
      setAiGenerationStatus('❌ Location data not available for AI generation');
      setTimeout(() => setAiGenerationStatus(''), 5000);
      return;
    }

    if (mode === 'edit' && !data.location) {
      setAiGenerationStatus('❌ Attraction location data not available for AI generation');
      setTimeout(() => setAiGenerationStatus(''), 5000);
      return;
    }

    setIsGeneratingDescription(true);
    setAiGenerationStatus('🤖 Generating AI-enhanced description using backend API...');

    try {
      // Gather contextual data - handle both create and edit modes
      let contextData;
      let aiRequest;

      if (mode === 'create' && selectedLocation) {
        // Create mode: use selectedLocation data
        contextData = await gatherContextData(selectedLocation);

        const safeContextData = {
          hostLocation: contextData?.hostLocation || { lat: 45.2923, lng: 14.2751 }, // Lovran coordinates
          nearbyPlaces: contextData?.nearbyPlaces || [],
          webContext: contextData?.webContext || 'Local attraction in Croatian coastal region'
        };

        aiRequest = {
          attraction_name: data.name || selectedLocation.displayName || selectedLocation.name,
          location: selectedLocation.formatted_address,
          attraction_type: data.attraction_type || getCategoryFromTypes(selectedLocation.types),
          current_description: data.description || '',
          host_location: 'Lovran, Croatia',
          distance_from_host: calculateDistance(
            safeContextData.hostLocation,
            normalizeToLatLng(selectedLocation.geometry.location)
          ),
          nearby_places: safeContextData.nearbyPlaces.map(place => ({
            name: place.displayName || place.name,
            types: place.types,
            rating: place.rating
          })),
          google_places_data: {
            rating: selectedLocation.rating,
            user_ratings_total: selectedLocation.user_ratings_total,
            price_level: selectedLocation.price_level,
            types: selectedLocation.types,
            website: selectedLocation.website,
            phone_number: selectedLocation.phone_number
          },
          enhancement_type: 'contextual_description'
        };
      } else if (mode === 'edit' && data.location) {
        // Edit mode: use existing attraction data
        // Parse location to get coordinates for distance calculation
        const hostLocation = { lat: 45.2923, lng: 14.2751 }; // Lovran coordinates

        aiRequest = {
          attraction_name: data.name || 'Attraction',
          location: data.location,
          attraction_type: data.attraction_type || 'attraction',
          current_description: data.description || '',
          host_location: 'Lovran, Croatia',
          distance_from_host: 'Unknown', // Will be calculated by backend if possible
          nearby_places: [], // No nearby places data in edit mode
          google_places_data: {
            rating: data.rating,
            user_ratings_total: data.user_ratings_total,
            price_level: data.price_level,
            types: data.category_tags || [],
            website: data.website,
            phone_number: data.phone_number
          },
          enhancement_type: 'contextual_description'
        };
      } else {
        throw new Error('Invalid mode or missing data for AI generation');
      }

      // Make API call to backend for AI generation
      const response = await fetch(`${API_BASE_URL}/api/v1/attractions/ai-enhance`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': localStorage.getItem('session_token') || ''
        },
        body: JSON.stringify(aiRequest)
      });

      if (response.status === 401) {
        setAiGenerationStatus(`❌ Session expired. Please reload the page to log in again.`);
        setTimeout(() => setAiGenerationStatus(''), 5000);
        setIsGeneratingDescription(false);
        return;
      }

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const result = await response.json();

      if (result.success && result.data?.enhanced_description) {
        onChange({ ...data, description: result.data.enhanced_description });
        setAiGenerationStatus(`✅ AI-enhanced description generated with local context!`);
        setTimeout(() => setAiGenerationStatus(''), 5000);
      } else {
        // Fallback to local generation if API fails
        // Pass null for selectedLocation in edit mode to trigger edit mode logic
        const fallbackDescription = generateFallbackDescription(
          mode === 'edit' ? null : selectedLocation,
          contextData
        );
        onChange({ ...data, description: fallbackDescription });
        setAiGenerationStatus(`✅ Enhanced description generated (local fallback)!`);
        setTimeout(() => setAiGenerationStatus(''), 5000);
      }
    } catch (error) {
      console.error('Error generating AI description:', error);

      // Generate fallback description
      try {
        // In edit mode, we might not have selectedLocation, so pass null
        const contextData = await gatherContextData(mode === 'edit' ? null : selectedLocation);
        const safeContextData = {
          hostLocation: contextData?.hostLocation || { lat: 45.2923, lng: 14.2751 },
          nearbyPlaces: contextData?.nearbyPlaces || [],
          webContext: contextData?.webContext || 'Local attraction in Croatian coastal region'
        };
        // Pass null for selectedLocation in edit mode to trigger edit mode logic
        const fallbackDescription = generateFallbackDescription(
          mode === 'edit' ? null : selectedLocation,
          safeContextData
        );
        onChange({ ...data, description: fallbackDescription });
        setAiGenerationStatus(`✅ Enhanced description generated (fallback)!`);
        setTimeout(() => setAiGenerationStatus(''), 5000);
      } catch (fallbackError) {
        setAiGenerationStatus(`❌ Description generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        setTimeout(() => setAiGenerationStatus(''), 5000);
      }
    } finally {
      setIsGeneratingDescription(false);
    }
  };

  /**
   * Gathers contextual data for AI description generation
   */
  const gatherContextData = async (selectedLocation: any) => {
    const contextData = {
      hostLocation: { lat: 45.2919, lng: 14.2747 }, // Lovran coordinates
      nearbyPlaces: Array.isArray(nearbyPlaces) ? nearbyPlaces.slice(0, 5) : [],
      webContext: '',
      generalVibe: ''
    };

    try {
      // For now, we'll use basic contextual data
      // In the future, this could be enhanced with web search capabilities
      console.log('Using basic contextual data for AI generation');

      // Ensure nearbyPlaces is always an array
      if (!Array.isArray(contextData.nearbyPlaces)) {
        contextData.nearbyPlaces = [];
      }

      // In edit mode, we might not have nearby places data
      if (mode === 'edit') {
        contextData.nearbyPlaces = [];
        contextData.webContext = 'Local attraction in Croatian coastal region';
      }
    } catch (error) {
      console.log('Context gathering failed, continuing with basic data:', error);
      // Ensure we always return valid data structure
      contextData.nearbyPlaces = [];
    }

    return contextData;
  };

  /**
   * Generates a fallback description when AI generation fails
   */
  const generateFallbackDescription = (selectedLocation: any, contextData: any): string => {
    if (mode === 'edit' && data.location) {
      // Edit mode: use existing attraction data
      const attractionName = data.name || 'Attraction';
      const location = data.location;
      const type = data.attraction_type || 'attraction';

      return `${attractionName} is a ${type} located in ${location}. This attraction offers visitors a unique experience in the beautiful Croatian coastal region. Guests staying in Lovran can easily reach this location and enjoy its offerings while exploring the surrounding area. The attraction is well-positioned for tourists looking to discover local culture and attractions beyond their accommodation.`;
    } else if (selectedLocation) {
      // Create mode: use selectedLocation data
      const attractionName = data.name || selectedLocation.displayName || selectedLocation.name;
      const location = selectedLocation.formatted_address;
      const distance = calculateDistance(
        contextData.hostLocation,
        normalizeToLatLng(selectedLocation.geometry?.location)
      );
      const type = data.attraction_type || getCategoryFromTypes(selectedLocation.types);

      return `${attractionName} is a ${type} located in ${location}, approximately ${distance} from Lovran. This attraction offers visitors a unique experience in the beautiful Croatian coastal region. Guests staying in Lovran can easily reach this location and enjoy its offerings while exploring the surrounding area. The attraction is well-positioned for tourists looking to discover local culture and attractions beyond their accommodation.`;
    } else {
      return 'Unable to generate description due to missing location data.';
    }
  };

  const normalizeToLatLng = (
    loc:
      | { lat?: number | (() => number); lng?: number | (() => number) }
      | null
      | undefined
  ): { lat: number; lng: number } | null => {
    if (!loc) return null;
    const lat = typeof loc.lat === "function" ? loc.lat() : loc.lat;
    const lng = typeof loc.lng === "function" ? loc.lng() : loc.lng;
    if (typeof lat !== "number" || typeof lng !== "number") return null;
    return { lat, lng };
  };

  /**
   * Calculates approximate distance between two points
   */
  const calculateDistance = (point1: { lat: number; lng: number } | null | undefined, point2: { lat: number; lng: number } | null | undefined): string => {
    // Validate input parameters
    if (!point1 || !point2 ||
      typeof point1.lat !== 'number' || typeof point1.lng !== 'number' ||
      typeof point2.lat !== 'number' || typeof point2.lng !== 'number') {
      return 'Distance unavailable';
    }

    const R = 6371; // Earth's radius in kilometers
    const dLat = (point2.lat - point1.lat) * Math.PI / 180;
    const dLng = (point2.lng - point1.lng) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(point1.lat * Math.PI / 180) * Math.cos(point2.lng * Math.PI / 180) *
      Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;

    if (distance < 1) {
      return `${Math.round(distance * 1000)}m`;
    } else if (distance < 10) {
      return `${distance.toFixed(1)}km`;
    } else {
      return `${Math.round(distance)}km`;
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'create' ? 'Create New Attraction' : 'Edit Attraction'}
          </h2>
          <Button
            onClick={onClose}
            variant="ghost"
            size="sm"
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </Button>
        </div>

        {/* Content */}
        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Attraction Name *
                </label>
                <Input
                  value={data.name || ''}
                  onChange={(e) => onChange({ ...data, name: e.target.value })}
                  placeholder="Enter attraction name"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Attraction Type
                </label>
                <select
                  value={data.attraction_type || ''}
                  onChange={(e) => onChange({ ...data, attraction_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select type</option>
                  {ATTRACTION_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Location Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Location *
              </label>
              <div className="relative">
                <Input
                  value={locationSearchQuery}
                  onChange={(e) => handleLocationInputChange(e.target.value)}
                  placeholder="Search for a location (e.g., Art kino Rijeka)"
                  className="pr-10"
                />
                {isSearchingLocation && (
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  </div>
                )}
              </div>

              {/* Search Results Dropdown */}
              {showSearchDropdown && searchResults.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                  {searchResults.map((place) => (
                    <div
                      key={place.place_id}
                      onClick={() => handlePlaceSelection(place)}
                      className="px-4 py-2 hover:bg-gray-100 cursor-pointer border-b border-gray-200 last:border-b-0"
                    >
                      <div className="font-medium text-gray-900">
                        {place.displayName || place.name}
                      </div>
                      <div className="text-sm text-gray-600">
                        {place.formatted_address}
                      </div>
                      {place.types && place.types.length > 0 && (
                        <div className="text-xs text-gray-500 mt-1">
                          {place.types.slice(0, 3).join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Selected Location Display */}
            {selectedLocation && (() => {
              const rawLat = selectedLocation.geometry?.location?.lat;
              const rawLng = selectedLocation.geometry?.location?.lng;
              const latResolved =
                typeof rawLat === "function" ? rawLat() : typeof rawLat === "number" ? rawLat : null;
              const lngResolved =
                typeof rawLng === "function" ? rawLng() : typeof rawLng === "number" ? rawLng : null;
              const latNum =
                latResolved ?? (typeof data.latitude === "number" ? data.latitude : null);
              const lngNum =
                lngResolved ?? (typeof data.longitude === "number" ? data.longitude : null);
              const mapAddress: string =
                selectedLocation.formatted_address || data.address || "";
              return (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-lg font-medium text-blue-900 mb-3">📍 Selected Location</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium text-blue-800 mb-2">
                      {selectedLocation.displayName || selectedLocation.name}
                    </h4>
                    <p className="text-sm text-blue-800 mb-2">
                      {selectedLocation.formatted_address || 'Address not available'}
                    </p>
                    <div className="flex items-center gap-4 text-sm mb-3">
                      <span className="text-gray-600">
                        📍 Lat: {latNum != null ? latNum.toFixed(6) : 'N/A'}, Lng: {lngNum != null ? lngNum.toFixed(6) : 'N/A'}
                      </span>
                    </div>
                    <div className="bg-gray-200 h-48 rounded-lg overflow-hidden">
                      {latNum != null && lngNum != null && google ? (
                        <GoogleMapPreview
                          latitude={latNum}
                          longitude={lngNum}
                          address={mapAddress}
                          google={google}
                          mapId={mapId ?? "DEMO_MAP_ID"}
                          onLocationAdjust={handleLocationAdjust}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full">
                          <div className="text-center">
                            <div className="text-2xl mb-2">🗺️</div>
                            <div className="text-sm text-gray-600">Select a location to view map</div>
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="mt-2 text-xs text-gray-600">
                      💡 Click on the map to adjust the exact location if needed
                    </div>
                  </div>
                </div>
              </div>
            );
            })()}

            {/* Selected Place Info */}
            {selectedLocation && (
              <div className="border-t pt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">📍 Selected Place Info</h3>
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium text-blue-900">
                      {selectedLocation.displayName || selectedLocation.name}
                    </h4>
                    <Badge variant="outline">
                      {getCategoryFromTypes(selectedLocation.types)}
                    </Badge>
                  </div>
                  <p className="text-sm text-blue-800 mb-2">
                    {selectedLocation.formatted_address}
                  </p>
                  <div className="flex items-center gap-4 text-sm mb-2">
                    {selectedLocation.rating && (
                      <span className="text-yellow-600">
                        ⭐ {selectedLocation.rating} ({selectedLocation.user_ratings_total} reviews)
                      </span>
                    )}
                    {selectedLocation.price_level && (
                      <span className="text-green-600">
                        {getPriceLevelText(selectedLocation.price_level)}
                      </span>
                    )}
                  </div>
                  {selectedLocation.website && (
                    <div className="text-sm text-blue-600 mb-1">
                      🌐 <a
                        href={selectedLocation.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline"
                      >
                        Visit Website
                      </a>
                    </div>
                  )}
                  {selectedLocation.phone_number && (
                    <div className="text-sm text-gray-600">
                      📞 {selectedLocation.phone_number}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Image Selection from Google Places */}
            {data.image_gallery && data.image_gallery.length > 0 && (
              <div className="border-t pt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">📸 Choose Featured Image</h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {data.image_gallery.map((url, idx) => (
                    <div 
                      key={idx} 
                      className={`relative cursor-pointer rounded-lg overflow-hidden border-2 aspect-square ${data.featured_image_url === url ? 'border-blue-500 shadow-md ring-2 ring-blue-200' : 'border-transparent hover:border-gray-300'}`}
                      onClick={() => onChange({ ...data, featured_image_url: url })}
                    >
                      <img src={url} alt={`Place image ${idx+1}`} className="w-full h-full object-cover" />
                      {data.featured_image_url === url && (
                        <div className="absolute top-1 right-1 bg-blue-500 text-white rounded-full p-0.5 shadow">
                          <Check className="h-3 w-3" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <div className="mt-2 text-xs text-gray-500">
                  Select the image that best represents this attraction. This will be shown on the map and in lists.
                </div>
              </div>
            )}

            {/* Nearby Places for AI Enhancement */}
            {nearbyPlaces.length > 0 && (
              <div className="border-t pt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  🏪 Nearby Places (AI Enhancement)
                </h3>
                <div className="space-y-2">
                  {nearbyPlaces.map((place) => (
                    <div key={place.place_id} className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-900">
                            {place.displayName || place.name}
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            {place.types?.join(', ')}
                          </div>
                        </div>
                        <div className="text-xs text-gray-500">
                          {place.rating && `⭐ ${place.rating}`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-2 text-xs text-gray-600">
                  💡 These nearby places will be used to enhance AI content generation
                </div>
              </div>
            )}

            {/* Additional Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  City
                </label>
                <Input
                  value={data.city || ''}
                  onChange={(e) => onChange({ ...data, city: e.target.value })}
                  placeholder="Enter city name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Address
                </label>
                <Input
                  value={data.address || ''}
                  onChange={(e) => onChange({ ...data, address: e.target.value })}
                  placeholder="Enter full address"
                />
              </div>
            </div>

            {/* Description with AI Enhancement */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Description *
                </label>
                {((selectedLocation && selectedLocation.geometry?.location) || (mode === 'edit' && data.location)) && (
                  <Button
                    type="button"
                    onClick={generateAIDescription}
                    disabled={isGeneratingDescription}
                    className="px-3 py-1 text-xs bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-md hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    title="Generate AI-enhanced description using Google Gemini with real-time search data"
                  >
                    {isGeneratingDescription ? (
                      <>
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                        AI...
                      </>
                    ) : (
                      <>
                        🤖 AI Enhance
                        <span className="text-xs bg-white bg-opacity-20 px-1 rounded">Gemini</span>
                      </>
                    )}
                  </Button>
                )}
              </div>

              {data.description && !isEditingDescription ? (
                <div className="relative">
                  <div className="w-full p-3 border border-gray-300 rounded-md bg-gray-50 min-h-[100px]">
                    {showRawMarkdown ? (
                      <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-white p-2 rounded border">
                        {data.description}
                      </pre>
                    ) : (
                      <MarkdownRenderer content={data.description} />
                    )}
                  </div>
                  <div className="absolute top-2 right-2 flex gap-2">
                    <Button
                      type="button"
                      onClick={() => setShowRawMarkdown(!showRawMarkdown)}
                      className={`px-2 py-1 text-xs rounded ${showRawMarkdown
                        ? 'bg-orange-600 hover:bg-orange-700'
                        : 'bg-purple-600 hover:bg-purple-700'
                        } text-white`}
                      title={showRawMarkdown ? "Show rendered view" : "Show raw markdown"}
                    >
                      {showRawMarkdown ? '👁️ View' : '📝 Raw'}
                    </Button>
                    <Button
                      type="button"
                      onClick={() => setIsEditingDescription(true)}
                      className="px-2 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700"
                    >
                      ✏️ Edit
                    </Button>
                    <Button
                      type="button"
                      onClick={() => {
                        const textArea = document.createElement('textarea');
                        textArea.value = data.description || '';
                        document.body.appendChild(textArea);
                        textArea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textArea);
                        // You could add a toast notification here
                      }}
                      className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                      title="Copy raw text"
                    >
                      📋 Copy
                    </Button>
                  </div>
                </div>
              ) : (
                <textarea
                  value={data.description || ''}
                  onChange={(e) => onChange({ ...data, description: e.target.value })}
                  placeholder="Describe the attraction... Use AI Enhance button to generate rich, contextual description with real-time information"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              )}

              {data.description && isEditingDescription && (
                <div className="mt-2 flex gap-2">
                  <Button
                    type="button"
                    onClick={() => setIsEditingDescription(false)}
                    className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    ✅ Done
                  </Button>
                  <Button
                    type="button"
                    onClick={() => setIsEditingDescription(false)}
                    className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700"
                  >
                    🔄 Reset
                  </Button>
                </div>
              )}

              {/* AI Generation Tips */}
              {((selectedLocation && selectedLocation.geometry?.location) || (mode === 'edit' && data.location)) && (
                <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <div className="text-blue-600 text-sm">💡</div>
                    <div className="text-xs text-blue-800">
                      <strong>AI Enhancement Available:</strong>{" "}
                      {`Click "AI Enhance" to generate a rich description that includes:`}
                      <ul className="mt-1 ml-4 list-disc space-y-1">
                        <li>
                          Contextual information about the attraction&apos;s relation to your Lovran location
                        </li>
                        <li>Real-time details about the place from web sources</li>
                        <li>General vibe and what people say about it</li>
                        <li>Practical tips for guests visiting from your area</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Admission Fee
                </label>
                <Input
                  value={data.admission_fee || ''}
                  onChange={(e) => onChange({ ...data, admission_fee: e.target.value })}
                  placeholder="e.g., Free, €10, etc."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Difficulty Level
                </label>
                <select
                  value={data.difficulty_level || ''}
                  onChange={(e) => onChange({ ...data, difficulty_level: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select difficulty</option>
                  <option value="easy">Easy</option>
                  <option value="moderate">Moderate</option>
                  <option value="challenging">Challenging</option>
                  <option value="expert">Expert</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category Tags
                </label>
                <Input
                  value={data.category_tags?.join(', ') || ''}
                  onChange={(e) => onChange({
                    ...data,
                    category_tags: e.target.value.split(',').map(tag => tag.trim()).filter(Boolean)
                  })}
                  placeholder="tag1, tag2, tag3"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Host Personal Tip
                </label>
                <textarea
                  value={data.host_personal_tip || ''}
                  onChange={(e) => onChange({ ...data, host_personal_tip: e.target.value })}
                  placeholder="Share your personal experience or insider tip..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Host Favorite Time
                </label>
                <Input
                  value={data.host_favorite_time || ''}
                  onChange={(e) => onChange({ ...data, host_favorite_time: e.target.value })}
                  placeholder="e.g., Sunset, Morning, Evening"
                />
              </div>
            </div>

            {/* AI Generation Status */}
            {aiGenerationStatus && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">{aiGenerationStatus}</p>
              </div>
            )}

            {/* Form Actions */}
            <div className="flex items-center justify-end gap-4 pt-6 border-t">
              <Button
                type="button"
                onClick={onClose}
                variant="outline"
                className="px-6"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="px-6 bg-blue-600 hover:bg-blue-700"
                disabled={isGeneratingContent}
              >
                {isGeneratingContent ? 'Creating...' : mode === 'create' ? 'Create Attraction' : 'Update Attraction'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default EnhancedAttractionModal;
