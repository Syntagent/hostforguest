"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useGoogleMaps } from "./GoogleMapsProvider";
import { locationsApi } from "@/lib/api";

interface Place {
  place_id: string;
  name: string;
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
      lat: number;
      lng: number;
    };
  };
}

interface HostLocationSearchProps {
  onSelectPlace: (place: Place) => void;
  onAddToAttractions: (place: Place) => void;
  className?: string;
}

export const HostLocationSearch: React.FC<HostLocationSearchProps> = ({
  onSelectPlace,
  onAddToAttractions,
  className
}) => {
  const { isLoaded, google } = useGoogleMaps();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Place[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedPlace, setSelectedPlace] = useState<Place | null>(null);
  const [placeDetails, setPlaceDetails] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const searchPlaces = async (query: string) => {
    if (!query.trim() || !google) return;

    setIsSearching(true);
    setError(null);

    try {
      // Use the new Place class instead of deprecated PlacesService
      const { Place } = (await google.maps.importLibrary("places")) as unknown as {
        Place: { searchByText: (req: Record<string, unknown>) => Promise<unknown> };
      };

      const request = {
        textQuery: `${query} Croatia`,
        fields: ['id', 'displayName', 'formattedAddress', 'types', 'rating', 'userRatingCount', 'priceLevel', 'photos', 'location']
      };

      const rawSearchResults = await Place.searchByText(request);
      const rawAny = rawSearchResults as unknown[] | { places?: unknown[] } | null | undefined;
      const places = Array.isArray(rawAny)
        ? rawAny
        : rawAny && typeof rawAny === "object" && Array.isArray((rawAny as { places: unknown[] }).places)
          ? (rawAny as { places: unknown[] }).places
          : [];
      
      setIsSearching(false);
      
      if (places && places.length > 0) {
        const mappedPlaces: Place[] = places.map((place: any) => ({
          place_id: place.id,
          name: place.displayName,
          formatted_address: place.formattedAddress,
          types: place.types || [],
          rating: place.rating,
          user_ratings_total: place.userRatingCount,
          price_level: place.priceLevel,
          photos: place.photos,
          geometry: {
            location: {
              lat: typeof place.location?.lat === 'function' ? place.location.lat() : (place.location?.lat || 0),
              lng: typeof place.location?.lng === 'function' ? place.location.lng() : (place.location?.lng || 0)
            }
          }
        }));
        
        setSearchResults(mappedPlaces);
      } else {
        setError("No places found. Try a different search term.");
        setSearchResults([]);
      }
    } catch (err) {
      setIsSearching(false);
      setError("Failed to search places. Please try again.");
      console.error("Error searching places:", err);
    }
  };

  const getPlaceDetails = async (placeId: string) => {
    if (!google) return;

    try {
      // Use the new Place class instead of deprecated PlacesService
      const { Place } = (await google.maps.importLibrary("places")) as unknown as {
        Place: new (opts: { id: string }) => {
          fetchFields: (opts: { fields: string[] }) => Promise<void>;
          displayName?: string;
          formattedAddress?: string;
          formattedPhoneNumber?: string;
          website?: string;
          openingHours?: { weekdayText?: string[] };
          rating?: number;
          userRatingCount?: number;
          priceLevel?: number;
          photos?: unknown[];
          types?: string[];
          location?: { lat?: number | (() => number); lng?: number | (() => number) };
          editorialSummary?: string;
          reviews?: unknown[];
        };
      };

      const place = new Place({ id: placeId });
      
      await place.fetchFields({
        fields: [
          'displayName',
          'formattedAddress',
          'formattedPhoneNumber',
          'website',
          'openingHours',
          'rating',
          'userRatingCount',
          'priceLevel',
          'photos',
          'types',
          'location',
          'editorialSummary',
          'reviews'
        ]
      });

      setPlaceDetails(place);
    } catch (err) {
      console.error("Error getting place details:", err);
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    
    // Debounce search
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (query.trim()) {
      searchTimeoutRef.current = setTimeout(() => {
        searchPlaces(query);
      }, 500);
    } else {
      setSearchResults([]);
    }
  };

  const handlePlaceSelect = (place: Place) => {
    setSelectedPlace(place);
    getPlaceDetails(place.place_id);
    onSelectPlace(place);
  };

  const getCategoryFromTypes = (types: string[]): string => {
    const typeMap: Record<string, string> = {
      'restaurant': 'Restaurant',
      'food': 'Restaurant',
      'cafe': 'Cafe',
      'bar': 'Cafe',
      'museum': 'Museum',
      'art_gallery': 'Museum',
      'church': 'Church',
      'place_of_worship': 'Church',
      'castle': 'Historical Site',
      'historic': 'Historical Site',
      'tourist_attraction': 'Historical Site',
      'park': 'Park',
      'natural_feature': 'Park',
      'beach': 'Beach',
      'amusement_park': 'Adventure Activity',
      'aquarium': 'Museum',
      'zoo': 'Park',
      'shopping_mall': 'Local Shop',
      'store': 'Local Shop',
      'market': 'Market',
      'winery': 'Winery',
      'spa': 'Wellness',
      'gym': 'Wellness',
      'hiking': 'Hiking Trail',
      'campground': 'Adventure Activity'
    };

    for (const type of types) {
      if (typeMap[type]) {
        return typeMap[type];
      }
    }

    return 'Other';
  };

  const getPriceLevelText = (level?: number): string => {
    if (!level) return 'Price not available';
    return '€'.repeat(level);
  };

  const getRatingStars = (rating?: number): string => {
    if (!rating) return 'No rating';
    return '⭐'.repeat(Math.round(rating));
  };

  return (
    <div className={className}>
      <Card>
        <CardHeader>
          <CardTitle>🔍 Discover New Places</CardTitle>
          <p className="text-sm text-gray-600">
            Search for local attractions, restaurants, and points of interest to add to your recommendations
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Search Input */}
            <div className="relative">
              <Input
                type="text"
                placeholder="Search for places in Croatia (e.g., 'Lovran restaurants', 'Istria beaches')"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className="pr-10"
              />
              {isSearching && (
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 bg-red-50 border border-red-200 rounded-lg"
              >
                <p className="text-sm text-red-600">{error}</p>
              </motion.div>
            )}

            {/* Search Results */}
            <AnimatePresence>
              {searchResults.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2"
                >
                  <h3 className="font-medium text-gray-900">
                    Found {searchResults.length} places
                  </h3>
                  
                  {searchResults.map((place) => (
                    <motion.div
                      key={place.place_id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors cursor-pointer"
                      onClick={() => handlePlaceSelect(place)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 mb-1">
                            {place.name}
                          </h4>
                          <p className="text-sm text-gray-600 mb-2">
                            {place.formatted_address}
                          </p>
                          
                          <div className="flex items-center gap-4 text-sm">
                            <Badge variant="outline">
                              {getCategoryFromTypes(place.types)}
                            </Badge>
                            
                            {place.rating && (
                              <span className="text-yellow-600">
                                {getRatingStars(place.rating)} ({place.rating})
                              </span>
                            )}
                            
                            {place.price_level && (
                              <span className="text-green-600">
                                {getPriceLevelText(place.price_level)}
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => {
                            e.stopPropagation();
                            onAddToAttractions(place);
                          }}
                        >
                          ➕ Add
                        </Button>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Selected Place Details */}
            <AnimatePresence>
              {selectedPlace && placeDetails && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="p-4 bg-blue-50 border border-blue-200 rounded-lg"
                >
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="font-medium text-blue-900">
                      📍 {placeDetails.name}
                    </h4>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setSelectedPlace(null);
                        setPlaceDetails(null);
                      }}
                    >
                      ✕
                    </Button>
                  </div>
                  
                  <div className="space-y-2 text-sm">
                    <div className="text-sm text-gray-600">
                      <strong>Address:</strong> {placeDetails.formatted_address}
                    </div>
                    <div className="text-sm text-gray-600">
                      <strong>Types:</strong> {placeDetails.types?.join(', ')}
                    </div>
                    {placeDetails.rating && (
                      <div className="text-sm text-gray-600">
                        <strong>Rating:</strong> ⭐ {placeDetails.rating} ({placeDetails.user_ratings_total} reviews)
                      </div>
                    )}
                    {placeDetails.website && (
                      <div className="text-sm text-gray-600">
                        <strong>Website:</strong> <a href={placeDetails.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{placeDetails.website}</a>
                      </div>
                    )}
                    {placeDetails.phone_number && (
                      <div className="text-sm text-gray-600">
                        <strong>Phone:</strong> {placeDetails.phone_number}
                      </div>
                    )}
                    {/* Removed open_now as it's deprecated */}
                    
                    {placeDetails.editorial_summary && (
                      <p className="text-blue-800">
                        <strong>Description:</strong> {placeDetails.editorial_summary.overview}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex gap-2 mt-4">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onAddToAttractions(selectedPlace)}
                    >
                      ➕ Add to Attractions
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setSelectedPlace(null);
                        setPlaceDetails(null);
                      }}
                    >
                      Close
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Search Tips */}
            {!searchQuery && searchResults.length === 0 && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium text-gray-900 mb-2">💡 Search Tips</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Try searching for specific areas: &quot;Lovran restaurants&quot;</li>
                  <li>• Search by activity: &quot;Istria hiking trails&quot;</li>
                  <li>• Look for cultural sites: &quot;Croatia museums&quot;</li>
                  <li>• Find local experiences: &quot;Opatija beaches&quot;</li>
                </ul>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
