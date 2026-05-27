"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { GoogleMapsProvider } from "@/components/maps/GoogleMapsProvider";
import { HostMapView, type HostMapViewHandle } from "@/components/maps/HostMapView";
import type { Attraction } from "@/lib/api";
import {
  BarChart3,
  Camera,
  Compass,
  Landmark,
  MapPin,
  Pencil,
  Plus,
  Trash2,
  Clock,
  Globe,
  Phone,
  Utensils,
  Coffee,
  ShoppingBag,
  Wine,
  Tent,
  Waves,
  Mountain,
  Castle,
  Church,
  Trees,
  Theater,
  Music,
  Activity
} from "lucide-react";

const getCategoryIconComponent = (category: string | undefined, className: string = "h-6 w-6 text-sky-600") => {
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

export const AttractionsTab: React.FC<{
  attractions: Attraction[];
  onCreateAttraction: () => void;
  onEditAttraction: (attraction: Attraction) => void;
  onDeleteAttraction: (attraction: Attraction) => void;
  onViewReviews: (attraction: Attraction) => void;
  onPhotoUpload: (attraction: Attraction) => void;
  viewMode: "list" | "map";
  onToggleViewMode: () => void;
}> = ({
  attractions,
  onCreateAttraction,
  onEditAttraction,
  onDeleteAttraction,
  onViewReviews,
  onPhotoUpload,
  viewMode,
  onToggleViewMode,
}) => {
  const hostMapRef = React.useRef<HostMapViewHandle | null>(null);
  const [selectedMapAttractionId, setSelectedMapAttractionId] = React.useState<string | null>(null);

  const handleViewOnMap = (attractionId: string) => {
    setSelectedMapAttractionId(attractionId);
    if (viewMode !== "map") {
      onToggleViewMode();
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-gray-900 sm:text-2xl">Croatian Attractions</h2>
          <p className="text-sm text-muted-foreground">
            Curated places and a live map in one integrated workspace.
          </p>
        </div>
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center">
          <div className="grid grid-cols-2 rounded-2xl border bg-muted/20 p-1">
            <Button 
              variant={viewMode === "list" ? "secondary" : "ghost"} 
              size="sm"
              onClick={() => viewMode !== "list" && onToggleViewMode()}
              className="h-8 rounded-xl"
            >
              List View
            </Button>
            <Button 
              variant={viewMode === "map" ? "secondary" : "ghost"} 
              size="sm"
              onClick={() => viewMode !== "map" && onToggleViewMode()}
              className="h-8 rounded-xl"
            >
              <Compass className="mr-2 h-4 w-4" />
              Map View
            </Button>
          </div>
          <Button gradient onClick={onCreateAttraction} className="w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" />
            Add New Attraction
          </Button>
        </div>
      </div>

      {attractions.length === 0 ? (
        <Card className="py-12 text-center">
          <CardContent>
            <div className="mb-4 flex justify-center">
              <Landmark className="h-14 w-14 text-muted-foreground" />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-gray-900">No Attractions Yet</h3>
            <p className="mb-6 text-gray-600">
              Start sharing your local Croatian experiences with guests. Add your first attraction
              to help visitors discover authentic places.
            </p>
            <Button gradient onClick={onCreateAttraction}>
              <Plus className="mr-2 h-4 w-4" />
              Create Your First Attraction
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {viewMode === "map" ? (
            <Card className="relative flex h-[58vh] min-h-[22rem] max-h-[calc(100dvh-10rem)] flex-col overflow-hidden border shadow-sm sm:h-[700px] sm:max-h-none">
              <div className="h-full w-full bg-slate-50 relative flex-1">
                <GoogleMapsProvider apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ""}>
                  <HostMapView
                    ref={hostMapRef}
                    attractions={attractions}
                    onSelectAttraction={onEditAttraction}
                    onAddNewAttraction={onCreateAttraction}
                    hideTitle
                    embedded
                    selectedAttractionId={selectedMapAttractionId}
                    className="absolute inset-0 h-full w-full"
                  />
                </GoogleMapsProvider>
              </div>
            </Card>
          ) : (
            <div className="space-y-4 mt-2">
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {attractions.map((attraction) => (
              <Card 
                key={attraction.id} 
                className="overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleViewOnMap(attraction.id)}
              >
                <div className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">
                          {attraction.category || attraction.attraction_type || "Attraction"}
                        </span>
                        {attraction.average_rating != null && (
                          <span className="flex items-center gap-1 text-[10px] font-medium text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-100">
                            ★ {attraction.average_rating.toFixed(1)} <span className="text-amber-600/70 font-normal">({attraction.review_count})</span>
                          </span>
                        )}
                        {attraction.cost_estimate && (
                          <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
                            {attraction.cost_estimate}
                          </span>
                        )}
                        {attraction.authenticity_level && (
                          <span className="text-[10px] font-medium text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-100">
                            {attraction.authenticity_level} authenticity
                          </span>
                        )}
                      </div>
                      <h3 className="truncate text-base font-semibold text-gray-900 leading-tight mb-1 group-hover:text-blue-600 transition-colors">{attraction.name}</h3>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3 w-3 shrink-0" />
                          <span className="truncate">{attraction.location || attraction.address || "Location not set"}</span>
                        </div>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="h-5 px-1.5 text-[10px] text-blue-600 hover:text-blue-700 hover:bg-blue-50 ml-1"
                          onClick={(e) => { e.stopPropagation(); handleViewOnMap(attraction.id); }}
                        >
                          <Compass className="h-3 w-3 mr-1" />
                          Map View
                        </Button>
                        {(attraction.duration_hours || attraction.difficulty_level) && (
                          <div className="flex items-center gap-2 border-l pl-2 border-gray-200">
                            {attraction.duration_hours && (
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                <span>~{attraction.duration_hours} hr{attraction.duration_hours !== 1 ? 's' : ''}</span>
                              </div>
                            )}
                            {attraction.difficulty_level && (
                              <div className="flex items-center gap-1">
                                <div className={`h-1.5 w-1.5 rounded-full ${
                                  attraction.difficulty_level === 'easy' ? 'bg-green-400' :
                                  attraction.difficulty_level === 'moderate' ? 'bg-yellow-400' :
                                  'bg-red-400'
                                }`} />
                                <span className="capitalize">{attraction.difficulty_level}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    {attraction.featured_image_url || (attraction.image_gallery && attraction.image_gallery.length > 0) ? (
                      <div className="h-12 w-12 rounded-lg bg-gray-100 overflow-hidden shrink-0 border border-gray-200">
                        <img src={attraction.featured_image_url || attraction.image_gallery?.[0]} alt={attraction.name} className="h-full w-full object-cover" />
                      </div>
                    ) : (
                      <div className="h-10 w-10 rounded-full bg-sky-50 flex items-center justify-center shrink-0 border border-sky-100 mt-0.5">
                        {getCategoryIconComponent(attraction.category || attraction.attraction_type, "h-5 w-5 text-sky-600")}
                      </div>
                    )}
                  </div>

                  <p className="line-clamp-2 text-xs text-gray-600 leading-relaxed">
                    {attraction.description || "No description available yet."}
                  </p>

                  {attraction.host_personal_tip && (
                    <div className="text-xs bg-indigo-50/60 p-2.5 rounded-md border border-indigo-100 text-indigo-900/90 shadow-sm relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-1 h-full bg-indigo-300"></div>
                      <span className="font-semibold text-indigo-700 uppercase tracking-wider block mb-0.5 text-[10px]">Host Tip</span>
                      <span className="italic">{`"${attraction.host_personal_tip}"`}</span>
                    </div>
                  )}

                  {(attraction.contact_info?.phone || attraction.contact_info?.website) && (
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                      {attraction.contact_info?.phone && (
                        <div className="flex items-center gap-1">
                          <Phone className="h-3 w-3 text-gray-400" />
                          <span>{attraction.contact_info.phone}</span>
                        </div>
                      )}
                      {attraction.contact_info?.website && (
                        <a 
                          href={attraction.contact_info.website} 
                          target="_blank" 
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="flex items-center gap-1 hover:text-blue-600 transition-colors text-blue-500 font-medium"
                        >
                          <Globe className="h-3 w-3" />
                          <span>Website</span>
                        </a>
                      )}
                    </div>
                  )}

                  <div className="flex flex-wrap gap-1.5 pt-2.5 border-t">
                    <Button size="sm" variant="outline" className="h-7 px-2 text-xs hover:bg-slate-50" onClick={(e) => { e.stopPropagation(); onEditAttraction(attraction); }}>
                      <Pencil className="mr-1.5 h-3 w-3 text-slate-500" />
                      Edit
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 px-2 text-xs hover:bg-slate-50" onClick={(e) => { e.stopPropagation(); onViewReviews(attraction); }}>
                      <BarChart3 className="mr-1.5 h-3 w-3 text-slate-500" />
                      Stats
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 px-2 text-xs hover:bg-slate-50" onClick={(e) => { e.stopPropagation(); onPhotoUpload(attraction); }}>
                      <Camera className="mr-1.5 h-3 w-3 text-slate-500" />
                      Photos {attraction.image_gallery && attraction.image_gallery.length > 0 ? `(${attraction.image_gallery.length})` : ''}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={(e) => { e.stopPropagation(); onDeleteAttraction(attraction); }}
                      className="h-7 px-2 text-xs text-red-600 hover:bg-red-50 hover:text-red-700 ml-auto"
                    >
                      <Trash2 className="mr-1.5 h-3 w-3" />
                      Delete
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
