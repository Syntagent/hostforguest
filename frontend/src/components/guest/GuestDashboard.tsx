"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import { useGuest } from "@/contexts/guest-context";
import { HeroSection } from "@/components/ui/hero-section";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InteractiveMap } from "@/components/maps/InteractiveMap";
import { GoogleMapsProvider } from "@/components/maps/GoogleMapsProvider";
import { locationsApi } from "@/lib/api";
import {
  MapPin,
  Calendar,
  Star,
  Heart,
  Clock,
  Users,
  Phone,
  Mail,
  Globe,
  Sun,
  Cloud,
  Umbrella,
  Map,
  Search
} from "lucide-react";

interface Recommendation {
  id: string;
  title: string;
  description: string;
  category: string;
  location: string;
  rating: number;
  price: string;
  image?: string;
  hostTip?: string;
  weatherDependent?: boolean;
  coordinates: {
    lat: number;
    lng: number;
  };
  source?: string;
  attraction_id?: string;
  place_id?: string;
}

interface WeatherInfo {
  temperature: number;
  condition: string;
  icon: string;
  forecast: string;
}

/** API row from locations list (guest group). */
interface GuestLocationApiRow {
  id: string;
  title: string;
  description?: string;
  category?: string;
  location?: string;
  rating?: number;
  price?: string;
  image?: string;
  hostTip?: string;
  weatherDependent?: boolean;
  coordinates?: { lat: number; lng: number };
  source?: string;
  attraction_id?: string;
  place_id?: string;
}

const SAMPLE_RECOMMENDATIONS: Recommendation[] = [
  {
    id: "1",
    title: "Plitvice Lakes National Park",
    description: "UNESCO World Heritage site with stunning waterfalls and crystal-clear lakes. Perfect for nature lovers and photography enthusiasts.",
    category: "Nature & Parks",
    location: "Plitvice Lakes",
    rating: 4.8,
    price: "€25-35",
    image: "/images/plitvice-lakes.jpg",
    hostTip: "Visit early morning to avoid crowds and get the best photos. Bring comfortable walking shoes and a water bottle.",
    weatherDependent: true,
    coordinates: { lat: 44.8654, lng: 15.5820 }
  },
  {
    id: "2",
    title: "Dubrovnik Old Town Walking Tour",
    description: "Explore the medieval walls and historic streets of the 'Pearl of the Adriatic'. Learn about Game of Thrones filming locations.",
    category: "Culture & History",
    location: "Dubrovnik",
    rating: 4.9,
    price: "€15-25",
    image: "/images/dubrovnik-old-town.jpg",
    hostTip: "Best time to visit is early morning or late afternoon. The city walls walk offers incredible sunset views.",
    weatherDependent: false,
    coordinates: { lat: 42.6507, lng: 18.0944 }
  },
  {
    id: "3",
    title: "Istrian Truffle Hunting Experience",
    description: "Join local truffle hunters and their dogs in the Istrian forests. Learn about truffle hunting traditions and enjoy a truffle tasting.",
    category: "Food & Wine",
    location: "Istria",
    rating: 4.7,
    price: "€80-120",
    image: "/images/truffle-hunting.jpg",
    hostTip: "Available year-round but autumn is the best season. Wear comfortable outdoor clothing and be prepared for a unique experience.",
    weatherDependent: true,
    coordinates: { lat: 45.3271, lng: 13.5952 }
  },
  {
    id: "4",
    title: "Hvar Island Wine Tasting",
    description: "Visit family-owned wineries on Hvar Island. Taste local Plavac Mali wines and learn about Croatian winemaking traditions.",
    category: "Food & Wine",
    location: "Hvar Island",
    rating: 4.6,
    price: "€45-65",
    image: "/images/hvar-wine.jpg",
    hostTip: "Combine with a sunset dinner at one of the wineries. Book in advance during peak season.",
    weatherDependent: false,
    coordinates: { lat: 43.1729, lng: 16.4428 }
  },
  {
    id: "5",
    title: "Zagreb Food Market Tour",
    description: "Explore Dolac Market and taste local Croatian specialties. Learn about traditional ingredients and cooking methods.",
    category: "Food & Wine",
    location: "Zagreb",
    rating: 4.5,
    price: "€30-45",
    image: "/images/zagreb-market.jpg",
    hostTip: "Visit on Saturday morning for the freshest produce and most authentic experience.",
    weatherDependent: false,
    coordinates: { lat: 45.8150, lng: 15.9819 }
  },
  {
    id: "6",
    title: "Rovinj Sunset Kayaking",
    description: "Paddle around the beautiful Rovinj archipelago during golden hour. Perfect for couples and adventure seekers.",
    category: "Adventure & Sports",
    location: "Rovinj",
    rating: 4.8,
    price: "€55-75",
    image: "/images/rovinj-kayaking.jpg",
    hostTip: "Best during summer months. No experience needed - guides provide full instruction.",
    weatherDependent: true,
    coordinates: { lat: 45.0819, lng: 13.6386 }
  }
];

const SAMPLE_WEATHER: WeatherInfo = {
  temperature: 22,
  condition: "Sunny",
  icon: "☀️",
  forecast: "Perfect weather for outdoor activities. Light breeze, low humidity."
};

export const GuestDashboard: React.FC = () => {
  const { guestGroup, preferences } = useGuest();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [weather, setWeather] = useState<WeatherInfo>(SAMPLE_WEATHER);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [favorites, setFavorites] = useState<string[]>([]);
  const [showMap, setShowMap] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState<Recommendation | null>(null);
  const [viewMode, setViewMode] = useState<"cards" | "map">("cards");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadLocations = async () => {
      if (!guestGroup?.id) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Fetch locations from the API (combines database attractions and Google Places)
        const response = await locationsApi.getForGuestGroup(guestGroup.id, {
          includeGooglePlaces: true,
          includeHostAttractions: true,
        });

        if (response.success && response.data) {
          // Transform API data to match our Recommendation interface
          const apiLocations: Recommendation[] = response.data.locations.map((location: GuestLocationApiRow) => ({
            id: location.id,
            title: location.title ?? "",
            description: location.description ?? "",
            category: location.category ?? "",
            location: location.location ?? "",
            rating: location.rating ?? 0,
            price: location.price ?? "",
            image: location.image || "/images/placeholder.jpg",
            hostTip: location.hostTip,
            weatherDependent: location.weatherDependent,
            coordinates: location.coordinates ?? { lat: 45.1, lng: 14.3 },
            source: location.source,
            attraction_id: location.attraction_id,
            place_id: location.place_id,
          }));

          setRecommendations(apiLocations);
        } else {
          // Fallback to sample data if API fails
          setRecommendations(SAMPLE_RECOMMENDATIONS);
        }
      } catch (err) {
        console.error("Failed to load locations:", err);
        setError("Failed to load locations. Using sample data.");
        // Fallback to sample data
        setRecommendations(SAMPLE_RECOMMENDATIONS);
      } finally {
        setLoading(false);
      }
    };

    loadLocations();
  }, [guestGroup?.id, preferences]);

  const filteredRecommendations = selectedCategory === "all"
    ? recommendations
    : recommendations.filter(rec => rec.category === selectedCategory);

  const categories = ["all", ...Array.from(new Set(recommendations.map(r => r.category)))];

  const toggleFavorite = (id: string) => {
    setFavorites(prev =>
      prev.includes(id)
        ? prev.filter(fav => fav !== id)
        : [...prev, id]
    );
  };

  const getWeatherIcon = (condition: string) => {
    switch (condition.toLowerCase()) {
      case "sunny": return <Sun className="w-6 h-6 text-yellow-500" />;
      case "cloudy": return <Cloud className="w-6 h-6 text-gray-500" />;
      case "rainy": return <Umbrella className="w-6 h-6 text-blue-500" />;
      default: return <Sun className="w-6 h-6 text-yellow-500" />;
    }
  };

  const handleLocationSelect = (location: Recommendation) => {
    setSelectedLocation(location);
  };

  // Add function to get directions
  const getDirections = async (destination: Recommendation) => {
    try {
      // This would integrate with Google Directions API
      const response = await fetch(`/api/directions?destination=${encodeURIComponent(destination.location)}&coordinates=${destination.coordinates.lat},${destination.coordinates.lng}`);
      if (response.ok) {
        const directions = await response.json();

        // Open Google Maps with directions
        const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination.location)}&travelmode=driving`;
        window.open(googleMapsUrl, '_blank');
      }
    } catch (error) {
      console.error('Failed to get directions:', error);
      // Fallback to Google Maps
      const googleMapsUrl = `https://www.google.com/maps/search/${encodeURIComponent(destination.location)}`;
      window.open(googleMapsUrl, '_blank');
    }
  };

  const toggleViewMode = () => {
    setViewMode(viewMode === "cards" ? "map" : "cards");
  };

  const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number) => {
    const R = 6371; // Radius of the earth in km
    const dLat = deg2rad(lat2 - lat1);
    const dLon = deg2rad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c; // Distance in km
  };

  const deg2rad = (deg: number) => {
    return deg * (Math.PI / 180);
  };

  const handleNearMe = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const userLat = position.coords.latitude;
        const userLng = position.coords.longitude;

        const sorted = [...recommendations].sort((a, b) => {
          const distA = calculateDistance(userLat, userLng, a.coordinates.lat, a.coordinates.lng);
          const distB = calculateDistance(userLat, userLng, b.coordinates.lat, b.coordinates.lng);
          return distA - distB;
        });

        setRecommendations(sorted);
        setLoading(false);
        // Reset category to show all sorted by distance
        setSelectedCategory("all");
      },
      (error) => {
        console.error("Error getting location:", error);
        setLoading(false);
        alert("Unable to retrieve your location");
      }
    );
  };

  const handleCardClick = (location: Recommendation) => {
    setSelectedLocation(location);
    setViewMode("map");
  };

  return (
    <div className="min-h-screen">
      <HeroSection
        title="Dobro došli u Hrvatsku! 🇭🇷"
        subtitle="Your Croatian Adventure Awaits"
        description={`Welcome back, ${guestGroup?.group_name || 'Guest'}! Here are your personalized Croatian recommendations.`}
        backgroundGradient="from-blue-600 via-teal-600 to-green-600"

      >
        <GoogleMapsProvider apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ""}>
          <div className="mt-8 max-w-6xl mx-auto px-4">
            {/* Weather & Quick Info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
            >
              <Card className="bg-white/10 backdrop-blur-sm border-white/20">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white flex items-center gap-2">
                    {getWeatherIcon(weather.condition)}
                    Current Weather
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-white">
                    <div className="text-3xl font-bold">{weather.temperature}°C</div>
                    <div className="text-lg">{weather.condition}</div>
                    <div className="text-sm opacity-80 mt-2">{weather.forecast}</div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/10 backdrop-blur-sm border-white/20">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white flex items-center gap-2">
                    <Calendar className="w-5 h-5" />
                    Your Stay
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-white">
                    <div className="text-lg font-semibold">5 days remaining</div>
                    <div className="text-sm opacity-80">Make the most of your time!</div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/10 backdrop-blur-sm border-white/20">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white flex items-center gap-2">
                    <Users className="w-5 h-5" />
                    Your Host
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-white">
                    <div className="text-lg font-semibold">Local Host</div>
                    <div className="text-sm opacity-80 flex items-center gap-1 mt-1">
                      <Phone className="w-3 h-3" />
                      Available 24/7
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>



            {/* View Mode Toggle & Category Filter */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="mb-8"
            >
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-2">
                  <Button
                    variant={viewMode === "cards" ? "secondary" : "outline"}
                    size="sm"
                    onClick={() => setViewMode("cards")}
                    className="bg-white/10 hover:bg-white/20 border-white/20 text-white"
                  >
                    <Search className="w-4 h-4 mr-2" />
                    List View
                  </Button>
                  <Button
                    variant={viewMode === "map" ? "secondary" : "outline"}
                    size="sm"
                    onClick={() => setViewMode("map")}
                    className="bg-white/10 hover:bg-white/20 border-white/20 text-white"
                  >
                    <Map className="w-4 h-4 mr-2" />
                    Map View
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleNearMe}
                    className="bg-white/10 hover:bg-white/20 border-white/20 text-white"
                  >
                    <MapPin className="w-4 h-4 mr-2" />
                    Near Me
                  </Button>
                </div>

                {viewMode === "cards" && (
                  <div className="flex flex-wrap gap-2">
                    {categories.map((category) => (
                      <Button
                        key={category}
                        variant={selectedCategory === category ? "secondary" : "outline"}
                        size="sm"
                        onClick={() => setSelectedCategory(category)}
                        className="bg-white/10 hover:bg-white/20 border-white/20 text-white"
                      >
                        {category === "all" ? "All Activities" : category}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>

            {/* Content Area */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {viewMode === "map" ? (
                // Map View
                <div className="space-y-6">
                  <InteractiveMap
                    locations={filteredRecommendations}
                    onLocationSelect={handleLocationSelect}
                    selectedLocationId={selectedLocation?.id}
                    className="w-full"
                  />

                  {selectedLocation && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg p-6"
                    >
                      <div className="flex justify-between items-start mb-4">
                        <h3 className="text-white text-xl font-semibold">{selectedLocation.title}</h3>
                        <div className="flex items-center gap-1 text-yellow-400">
                          <Star className="w-4 h-4 fill-current" />
                          <span className="text-sm">{selectedLocation.rating}</span>
                        </div>
                      </div>
                      <p className="text-white/80 mb-4">{selectedLocation.description}</p>
                      <div className="flex justify-between items-center">
                        <Badge variant="secondary" className="bg-white/20 text-white">
                          {selectedLocation.category}
                        </Badge>
                        <span className="text-white font-semibold">{selectedLocation.price}</span>
                      </div>
                      {selectedLocation.hostTip && (
                        <div className="mt-4 bg-blue-500/20 border border-blue-400/30 rounded-lg p-3">
                          <p className="text-blue-100 text-sm">
                            <strong>Host Tip:</strong> {selectedLocation.hostTip}
                          </p>
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>
              ) : (
                // Cards View
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {filteredRecommendations.map((recommendation, index) => (
                    <motion.div
                      key={recommendation.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <Card 
                        className="bg-white/10 backdrop-blur-sm border-white/20 overflow-hidden hover:bg-white/20 transition-colors cursor-pointer"
                        onClick={() => handleCardClick(recommendation)}
                      >
                        <div className="relative h-48">
                          <Image
                            src={recommendation.image || "/images/placeholder.jpg"}
                            alt={recommendation.title}
                            fill
                            className="object-cover"
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            className="absolute top-2 right-2 bg-black/20 hover:bg-black/40 text-white rounded-full"
                            onClick={(e) => { e.stopPropagation(); toggleFavorite(recommendation.id); }}
                          >
                            <Heart
                              className={`w-4 h-4 ${favorites.includes(recommendation.id) ? 'fill-red-500 text-red-500' : 'text-white'}`}
                            />
                          </Button>
                          {recommendation.weatherDependent && (
                            <Badge className="absolute top-2 left-2 bg-yellow-500/80 text-black">
                              Weather Dependent
                            </Badge>
                          )}
                        </div>

                        <CardHeader className="pb-3">
                          <div className="flex justify-between items-start">
                            <CardTitle className="text-white text-lg">{recommendation.title}</CardTitle>
                            <div className="flex items-center gap-1 text-yellow-400">
                              <Star className="w-4 h-4 fill-current" />
                              <span className="text-sm">{recommendation.rating}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 text-sm text-blue-200">
                            <MapPin className="w-3 h-3" />
                            {recommendation.location}
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-5 px-1.5 text-[10px] text-blue-300 hover:text-white hover:bg-white/10 ml-1"
                              onClick={(e) => { e.stopPropagation(); handleCardClick(recommendation); }}
                            >
                              <Map className="h-3 w-3 mr-1" />
                              Map View
                            </Button>
                          </div>
                        </CardHeader>

                        <CardContent className="pt-0">
                          <p className="text-white/80 text-sm mb-4 line-clamp-3">
                            {recommendation.description}
                          </p>

                          <div className="flex justify-between items-center mb-4">
                            <Badge variant="secondary" className="bg-white/20 text-white">
                              {recommendation.category}
                            </Badge>
                            <span className="text-white font-semibold">{recommendation.price}</span>
                          </div>

                          {recommendation.hostTip && (
                            <div className="bg-blue-500/20 border border-blue-400/30 rounded-lg p-3 mb-4">
                              <div className="flex items-start gap-2">
                                <div className="text-blue-300 text-sm">💡</div>
                                <div className="text-blue-100 text-sm">
                                  <strong>Host Tip:</strong> {recommendation.hostTip}
                                </div>
                              </div>
                            </div>
                          )}

                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1 bg-white/10 hover:bg-white/20 border-white/20 text-white"
                              onClick={(e) => { e.stopPropagation(); getDirections(recommendation); }}
                            >
                              🗺️ Get Directions
                            </Button>
                            <Button
                              size="sm"
                              className="flex-1 bg-blue-600 hover:bg-blue-700"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Book Now
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Quick Actions */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mt-12 text-center"
            >
              <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg p-6">
                <h3 className="text-white text-xl font-semibold mb-4">Need Help?</h3>
                <div className="flex flex-wrap gap-4 justify-center">
                  <Button variant="outline" className="bg-white/10 hover:bg-white/20 border-white/20 text-white">
                    <Phone className="w-4 h-4 mr-2" />
                    Contact Host
                  </Button>
                  <Button variant="outline" className="bg-white/10 hover:bg-white/20 border-white/20 text-white">
                    <Mail className="w-4 h-4 mr-2" />
                    Send Message
                  </Button>
                  <Button variant="outline" className="bg-white/10 hover:bg-white/20 border-white/20 text-white">
                    <Globe className="w-4 h-4 mr-2" />
                    Emergency Info
                  </Button>
                </div>
              </div>
            </motion.div>
          </div>
        </GoogleMapsProvider>
      </HeroSection>
    </div>
  );
};
