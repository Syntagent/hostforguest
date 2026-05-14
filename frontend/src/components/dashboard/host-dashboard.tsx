"use client";

import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn, isPlausibleGpsLatLng } from "@/lib/utils";
import {
  ChartNoAxesColumn,
  CarFront,
  Compass,
  House,
  Landmark,
  Lightbulb,
  Link2,
  Lock,
  LogIn,
  Map,
  MapPin,
  RefreshCw,
  Search,
  Sparkles,
  Star,
  Target,
  Users,
  Wrench,
  Plus,
  X,
  Route,
  Palette,
} from "lucide-react";
import { hostsApi, guestGroupsApi, attractionsApi, realtimeApi, HostProfile, GuestGroup, Attraction, GuestEVisitorData, GuestEVisitorDataCreate, API_BASE_URL } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import type { CreateGroupFormData, DashboardAnalytics } from "./dashboard-types";
import { AppLayout } from "@/components/layout/app-layout";
import { HostDashboardMainContent } from "./widgets/host-dashboard-main-content";
import { HostDashboardModals } from "./modals/host-dashboard-modals";

interface HostDashboardProps {
  className?: string;
}

export const HostDashboard: React.FC<HostDashboardProps> = ({ className }) => {
  const { user: currentHost, logout, devLogin } = useAuth();
  const [profile, setProfile] = useState<HostProfile | null>(null);
  const [guestGroups, setGuestGroups] = useState<GuestGroup[]>([]);
  const [attractions, setAttractions] = useState<Attraction[]>([]);
  const [realtimeUpdates, setRealtimeUpdates] = useState<Array<{ id: string; title: string; content: string; description?: string; created_at: string }>>([]);
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  /** After first successful load cycle, never swap the whole page for a skeleton (avoids "blank" UI while refresh runs). */
  const [dashboardReady, setDashboardReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  type DashboardTab = 'overview' | 'accommodation' | 'channels' | 'groups' | 'attractions' | 'routes' | 'maintenance' | 'adaptation' | 'insights' | 'map' | 'discover' | 'cleaning';
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');

  // Guest Groups state
  const [showCreateGroupModal, setShowCreateGroupModal] = useState(false);
  const [showGroupDetailsModal, setShowGroupDetailsModal] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<GuestGroup | null>(null);
  const [regeneratingGroupId, setRegeneratingGroupId] = useState<string | null>(null);
  const [createGroupData, setCreateGroupData] = useState<CreateGroupFormData>({
    group_name: '',
    group_size: 2,
    preferences: [{
      guest_name: '',
      age_range: 'adult',
      interests: [],
      mobility_level: 'high',
      budget_level: 'medium',
      language_preference: 'en'
    }]
  });

  // Attractions state
  const [showCreateAttractionModal, setShowCreateAttractionModal] = useState(false);
  const [showEditAttractionModal, setShowEditAttractionModal] = useState(false);
  const [showDeleteAttractionModal, setShowDeleteAttractionModal] = useState(false);
  const [showAnalyticsModal, setShowAnalyticsModal] = useState(false);
  const [showPhotoUploadModal, setShowPhotoUploadModal] = useState(false);
  const [selectedAttraction, setSelectedAttraction] = useState<Attraction | null>(null);
  const [createAttractionData, setCreateAttractionData] = useState({
    name: '',
    description: '',
    attraction_type: 'cultural', // Required field
    city: '', // Required field
    address: '',
    region: '',
    county: '',
    latitude: null as number | null,
    longitude: null as number | null,
    category_tags: [] as string[],
    host_personal_tip: '',
    host_favorite_time: '',
    host_insider_info: '',
    host_story: '',
    host_recommended_duration: '',
    opening_hours: {} as Record<string, any>,
    admission_fee: '',
    contact_info: {} as Record<string, string>,
    difficulty_level: 'easy',
    duration_hours: null as number | null,
    group_size_recommendation: '',
    seasonal_availability: 'year_round',
    best_months: [] as number[],
    seasonal_notes: '',
    featured_image_url: null as string | null,
    image_gallery: [] as string[],
    google_place_id: "",
    google_maps_url: "" as string | null,
  });

  // Google Maps and Places state
  const [selectedPlace, setSelectedPlace] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');

  // E-Visitor state
  const [showEVisitorModal, setShowEVisitorModal] = useState(false);
  const [evisitorData, setEvisitorData] = useState<GuestEVisitorData[]>([]);
  const [showCreateEVisitorModal, setShowCreateEVisitorModal] = useState(false);
  const [showEditEVisitorModal, setShowEditEVisitorModal] = useState(false);
  const [selectedEVisitor, setSelectedEVisitor] = useState<GuestEVisitorData | null>(null);
  const [createEVisitorData, setCreateEVisitorData] = useState<GuestEVisitorDataCreate>({
    first_name: '',
    last_name: '',
    date_of_birth: '',
    nationality: '',
    id_type: 'passport',
    id_number: '',
    id_issuing_country: '',
    arrival_date: '',
    departure_date: '',
    email: '',
    phone: ''
  });

  const [devTokenPresent, setDevTokenPresent] = useState<boolean | null>(null);
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    setDevTokenPresent(
      !!(typeof window !== "undefined" && localStorage.getItem("session_token"))
    );
  }, [currentHost]);

  useEffect(() => {
    if (!currentHost?.id) return;
    loadDashboardData();
  }, [currentHost?.id]);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Check if user is authenticated
      if (!currentHost) {
        console.error('No authenticated user found');
        setError('Authentication required. Please log in again.');
        return;
      }

      // Load host analytics data
      const analyticsResponse = await hostsApi.getAnalytics();
      if (analyticsResponse.success && analyticsResponse.data) {
        setAnalytics(analyticsResponse.data);
      } else if (analyticsResponse.status === 401) {
        console.error('Authentication failed for analytics');
        logout();
        return;
      }

      // Load host profile
      const hostResponse = await hostsApi.getProfile();
      if (hostResponse.success && hostResponse.data) {
        setProfile(hostResponse.data);
      } else if (hostResponse.status === 401) {
        console.error('Authentication failed for profile');
        logout();
        return;
      }

      // Load guest groups
      const groupsResponse = await guestGroupsApi.getByHost();
      if (groupsResponse.success && groupsResponse.data) {
        setGuestGroups(groupsResponse.data);
      } else if (groupsResponse.status === 401) {
        console.error('Authentication failed for guest groups');
        logout();
        return;
      }

      // Load attractions
      const attractionsResponse = await attractionsApi.getByHost();
      if (attractionsResponse.success && attractionsResponse.data) {
        setAttractions(attractionsResponse.data);
      } else if (attractionsResponse.status === 401) {
        console.error('Authentication failed for attractions');
        logout();
        return;
      }

      // Load real-time updates from Crawl4AI
      const realtimeResponse = await realtimeApi.getUpdates();
      if (realtimeResponse.success && realtimeResponse.data) {
        setRealtimeUpdates(realtimeResponse.data.slice(0, 5)); // Latest 5 updates
      } else if (realtimeResponse.status === 401) {
        console.error('Authentication failed for real-time updates');
        logout();
        return;
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
      setDashboardReady(true);
    }
  };

  const handleCreateGroup = async () => {
    try {
      const response = await guestGroupsApi.create(createGroupData);
      if (response.success && response.data) {
        setGuestGroups([...guestGroups, response.data]);
        setShowCreateGroupModal(false);
        setCreateGroupData({
          group_name: '',
          group_size: 2,
          preferences: [{
            guest_name: '',
            age_range: 'adult',
            interests: [],
            mobility_level: 'high',
            budget_level: 'medium',
            language_preference: 'en'
          }]
        });
        // Reload dashboard data to update analytics
        await loadDashboardData();
      }
    } catch (error) {
      console.error('Error creating guest group:', error);
    }
  };

  const copyAccessCode = (accessCode: string) => {
    const text = String(accessCode ?? "").trim();
    if (!text) {
      window.alert(
        "No access code is available for this group yet. Open View Details, or generate a new code from the group actions."
      );
      return;
    }
    void (async () => {
      try {
        await navigator.clipboard.writeText(text);
        window.alert("Access code copied to clipboard.");
      } catch {
        try {
          const ta = document.createElement("textarea");
          ta.value = text;
          ta.setAttribute("readonly", "");
          ta.style.position = "fixed";
          ta.style.left = "-9999px";
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          const ok = document.execCommand("copy");
          document.body.removeChild(ta);
          if (ok) {
            window.alert("Access code copied to clipboard.");
          } else {
            window.prompt("Copy this access code (Ctrl+C, then Enter):", text);
          }
        } catch {
          window.prompt("Copy this access code (Ctrl+C, then Enter):", text);
        }
      }
    })();
  };

  const handleRegenerateAccessCode = async (groupId: string) => {
    setRegeneratingGroupId(groupId);
    try {
      const res = await guestGroupsApi.regenerateAccessCode(groupId);
      if (!res.success || !res.data) {
        window.alert(res.error || "Could not generate access code. Is the API running the latest version?");
        return;
      }
      const raw = res.data as Record<string, unknown>;
      const code =
        typeof raw.code === "string"
          ? raw.code.trim()
          : typeof (raw as { Code?: string }).Code === "string"
            ? String((raw as { Code: string }).Code).trim()
            : "";
      if (!code) {
        window.alert(
          "The API responded but did not include an access code. Check the Network tab for POST …/regenerate-code."
        );
        return;
      }
      setGuestGroups((prev) =>
        prev.map((g) => (String(g.id) === String(groupId) ? { ...g, access_code: code } : g)),
      );
      setSelectedGroup((prev) =>
        prev && String(prev.id) === String(groupId) ? { ...prev, access_code: code } : prev,
      );
      // Clipboard after `await` often loses the user gesture — still try, then always show the code.
      let clipboardOk = false;
      try {
        if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(code);
          clipboardOk = true;
        }
      } catch {
        clipboardOk = false;
      }
      window.alert(
        clipboardOk
          ? `Access code copied to clipboard.\n\n${code}\n\nYou can also use Copy in group details.`
          : `New access code (copy manually — select text below):\n\n${code}`,
      );
    } catch (e) {
      console.error(e);
      window.alert("Could not generate access code.");
    } finally {
      setRegeneratingGroupId(null);
    }
  };

  // Attraction handlers
  const handleCreateAttraction = async () => {
    try {
      // Check if user is authenticated
      if (!currentHost) {
        console.error('No authenticated user found for attraction creation');
        setError('Authentication required. Please log in again.');
        return;
      }

      // Validate required fields
      if (
        !createAttractionData.name ||
        !createAttractionData.description ||
        !createAttractionData.attraction_type ||
        !createAttractionData.city ||
        typeof createAttractionData.latitude !== "number" ||
        typeof createAttractionData.longitude !== "number"
      ) {
        setError('Please fill in all required fields (name, description, attraction type, city, geolocation)');
        return;
      }

      const response = await attractionsApi.create(createAttractionData);
      if (response.success && response.data) {
        setAttractions([...attractions, response.data]);
        setShowCreateAttractionModal(false);
        setSelectedPlace(null);
        setCreateAttractionData({
          name: '',
          description: '',
          attraction_type: 'cultural',
          city: '',
          address: '',
          region: '',
          county: '',
          latitude: null,
          longitude: null,
          category_tags: [],
          host_personal_tip: '',
          host_favorite_time: '',
          host_insider_info: '',
          host_story: '',
          host_recommended_duration: '',
          opening_hours: {},
          admission_fee: '',
          contact_info: {},
          difficulty_level: 'easy',
          duration_hours: null,
          group_size_recommendation: '',
          seasonal_availability: 'year_round',
          best_months: [],
          seasonal_notes: '',
          featured_image_url: null,
          image_gallery: [],
          google_place_id: "",
          google_maps_url: null,
        });
        // Reload dashboard data to update analytics
        await loadDashboardData();
      } else if (response.status === 401) {
        console.error('Authentication failed for attraction creation');
        logout();
      } else if (response.status === 422) {
        console.error('Validation error:', response.error);
        setError(`Validation error: ${response.error}`);
      } else {
        console.error('Failed to create attraction:', response.error);
        setError(`Failed to create attraction: ${response.error}`);
      }
    } catch (error) {
      console.error('Error creating attraction:', error);
      setError('Network error occurred while creating attraction');
    }
  };

  const handleEditAttraction = async () => {
    if (!selectedAttraction) return;

    try {
      // Check if user is authenticated
      if (!currentHost) {
        console.error('No authenticated user found for attraction update');
        setError('Authentication required. Please log in again.');
        return;
      }

      // Validate required fields
      if (
        !createAttractionData.name ||
        !createAttractionData.description ||
        !createAttractionData.attraction_type ||
        !createAttractionData.city ||
        typeof createAttractionData.latitude !== "number" ||
        typeof createAttractionData.longitude !== "number"
      ) {
        setError('Please fill in all required fields (name, description, attraction type, city, geolocation)');
        return;
      }

      const response = await attractionsApi.update(selectedAttraction.id, createAttractionData);
      if (response.success && response.data) {
        setAttractions(attractions.map(attraction =>
          attraction.id === selectedAttraction.id ? response.data! : attraction
        ));
        setShowEditAttractionModal(false);
        setSelectedAttraction(null);
        setSelectedPlace(null);
        setCreateAttractionData({
          name: '',
          description: '',
          attraction_type: 'cultural',
          city: '',
          address: '',
          region: '',
          county: '',
          latitude: null,
          longitude: null,
          category_tags: [],
          host_personal_tip: '',
          host_favorite_time: '',
          host_insider_info: '',
          host_story: '',
          host_recommended_duration: '',
          opening_hours: {},
          admission_fee: '',
          contact_info: {},
          difficulty_level: 'easy',
          duration_hours: null,
          group_size_recommendation: '',
          seasonal_availability: 'year_round',
          best_months: [],
          seasonal_notes: '',
          featured_image_url: null,
          image_gallery: [],
          google_place_id: "",
          google_maps_url: null,
        });
        // Reload dashboard data to update analytics
        await loadDashboardData();
      } else if (response.status === 401) {
        console.error('Authentication failed for attraction update');
        logout();
      } else if (response.status === 422) {
        console.error('Validation error:', response.error);
        setError(`Validation error: ${response.error}`);
      } else {
        console.error('Failed to update attraction:', response.error);
        setError(`Failed to update attraction: ${response.error}`);
      }
    } catch (error) {
      console.error('Error updating attraction:', error);
      setError('Network error occurred while updating attraction');
    }
  };

  // E-Visitor handlers
  const loadEVisitorData = async (groupId: string) => {
    try {
      const response = await guestGroupsApi.getEVisitorData(groupId);
      if (response.success && response.data) {
        setEvisitorData(response.data);
      }
    } catch (error) {
      console.error('Error loading e-visitor data:', error);
    }
  };

  const handleCreateEVisitor = async () => {
    if (!selectedGroup) return;

    try {
      const response = await guestGroupsApi.createEVisitorData(selectedGroup.id, createEVisitorData);
      if (response.success && response.data) {
        setEvisitorData([...evisitorData, response.data]);
        setShowCreateEVisitorModal(false);
        setCreateEVisitorData({
          first_name: '',
          last_name: '',
          date_of_birth: '',
          nationality: '',
          id_type: 'passport',
          id_number: '',
          id_issuing_country: '',
          arrival_date: '',
          departure_date: '',
          email: '',
          phone: ''
        });
      }
    } catch (error) {
      console.error('Error creating e-visitor data:', error);
    }
  };

  const handleUpdateEVisitor = async () => {
    if (!selectedEVisitor || !selectedGroup) return;

    try {
      const response = await guestGroupsApi.updateEVisitorData(selectedGroup.id, selectedEVisitor.id, createEVisitorData);
      if (response.success && response.data) {
        setEvisitorData(evisitorData.map(ev =>
          ev.id === selectedEVisitor.id ? response.data! : ev
        ));
        setShowEditEVisitorModal(false);
        setSelectedEVisitor(null);
        setCreateEVisitorData({
          first_name: '',
          last_name: '',
          date_of_birth: '',
          nationality: '',
          id_type: 'passport',
          id_number: '',
          id_issuing_country: '',
          arrival_date: '',
          departure_date: '',
          email: '',
          phone: ''
        });
      }
    } catch (error) {
      console.error('Error updating e-visitor data:', error);
    }
  };

  const handleDeleteEVisitor = async (evisitorId: string) => {
    if (!selectedGroup) return;

    try {
      const response = await guestGroupsApi.deleteEVisitorData(selectedGroup.id, evisitorId);
      if (response.success) {
        setEvisitorData(evisitorData.filter(ev => ev.id !== evisitorId));
      }
    } catch (error) {
      console.error('Error deleting e-visitor data:', error);
    }
  };

  const handleMarkEVisitorRegistered = async (evisitorId: string, confirmationNumber: string) => {
    if (!selectedGroup) return;

    try {
      const response = await guestGroupsApi.markEVisitorRegistered(selectedGroup.id, evisitorId, confirmationNumber);
      if (response.success && response.data) {
        setEvisitorData(evisitorData.map(ev =>
          ev.id === evisitorId ? response.data! : ev
        ));
      }
    } catch (error) {
      console.error('Error marking e-visitor as registered:', error);
    }
  };

  const handleDeleteAttraction = async () => {
    if (!selectedAttraction) return;

    try {
      const response = await attractionsApi.delete(selectedAttraction.id);
      if (response.success) {
        setAttractions(attractions.filter(attraction => attraction.id !== selectedAttraction.id));
        setShowDeleteAttractionModal(false);
        setSelectedAttraction(null);
        // Reload dashboard data to update analytics
        await loadDashboardData();
      } else {
        console.error('Failed to delete attraction:', response.error);
      }
    } catch (error) {
      console.error('Error deleting attraction:', error);
    }
  };

  const openCreateAttractionModal = () => {
    setCreateAttractionData({
      name: '',
      description: '',
      attraction_type: 'cultural',
      city: '',
      address: '',
      region: '',
      county: '',
      latitude: null,
      longitude: null,
      category_tags: [],
      host_personal_tip: '',
      host_favorite_time: '',
      host_insider_info: '',
      host_story: '',
      host_recommended_duration: '',
      opening_hours: {},
      admission_fee: '',
      contact_info: {},
      difficulty_level: 'easy',
      duration_hours: null,
      group_size_recommendation: '',
      seasonal_availability: 'year_round',
      best_months: [],
      seasonal_notes: '',
      featured_image_url: null,
      image_gallery: [],
      google_place_id: "",
      google_maps_url: null,
    });
    setSelectedPlace(null);
    setShowCreateAttractionModal(true);
  };

  const openEditAttractionModal = (attraction: Attraction) => {
    setSelectedAttraction(attraction);
    setSelectedPlace(null);
    setCreateAttractionData({
      name: attraction.name,
      description: attraction.description,
      attraction_type: attraction.attraction_type || 'cultural',
      city: attraction.city || '',
      address: attraction.address || '',
      region: attraction.region || '',
      county: attraction.county || '',
      latitude: attraction.latitude ?? null,
      longitude: attraction.longitude ?? null,
      category_tags: attraction.category_tags || [],
      host_personal_tip: attraction.host_personal_tip || '',
      host_favorite_time: attraction.host_favorite_time || '',
      host_insider_info: attraction.host_insider_info || '',
      host_story: attraction.host_story || '',
      host_recommended_duration: attraction.host_recommended_duration || '',
      opening_hours: attraction.opening_hours || {},
      admission_fee: attraction.admission_fee || '',
      contact_info: attraction.contact_info || {},
      difficulty_level: attraction.difficulty_level || 'easy',
      duration_hours: attraction.duration_hours ?? null,
      group_size_recommendation: attraction.group_size_recommendation || '',
      seasonal_availability: attraction.seasonal_availability || 'year_round',
      best_months: attraction.best_months || [],
      seasonal_notes: attraction.seasonal_notes || '',
      featured_image_url: attraction.featured_image_url || null,
      image_gallery: attraction.image_gallery || [],
      google_place_id: attraction.google_place_id || "",
      google_maps_url: null,
    });
    setShowEditAttractionModal(true);
  };

  const openDeleteAttractionModal = (attraction: Attraction) => {
    setSelectedAttraction(attraction);
    setShowDeleteAttractionModal(true);
  };

  const openViewReviewsModal = (attraction: Attraction) => {
    setSelectedAttraction(attraction);
    setShowAnalyticsModal(true);
  };

  const openPhotoUploadModal = (attraction: Attraction) => {
    setSelectedAttraction(attraction);
    setShowPhotoUploadModal(true);
  };

  const handlePhotoUpload = async (attractionId: string, photos: File[]) => {
    const maxBytes = 1_500_000;
    for (const f of photos) {
      if (f.size > maxBytes) {
        throw new Error(
          `Each image must be under ${Math.round(maxBytes / 1e6)}MB so the API request stays reliable.`
        );
      }
    }
    const readDataUrl = (file: File) =>
      new Promise<string>((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(String(r.result));
        r.onerror = () => reject(new Error("Failed to read image file"));
        r.readAsDataURL(file);
      });
    const newUrls: string[] = [];
    for (const p of photos) {
      newUrls.push(await readDataUrl(p));
    }
    const current = attractions.find((a) => a.id === attractionId);
    const existing = Array.isArray(current?.image_gallery) ? current.image_gallery : [];
    const merged = [...existing, ...newUrls];
    const res = await attractionsApi.update(attractionId, { image_gallery: merged });
    if (!res.success) {
      throw new Error(res.error || "Failed to save images on the attraction");
    }
    await loadDashboardData();
  };

  // Add function to load Google Reviews
  const loadGoogleReviews = async (attraction: Attraction) => {
    if (!attraction.google_place_id) return null;

    try {
      // This would call a backend endpoint that fetches Google Reviews
      const response = await fetch(`/api/attractions/${attraction.id}/google-reviews`);
      if (response.ok) {
        const googleReviews = await response.json();
        return googleReviews;
      }
    } catch (error) {
      console.error('Failed to load Google Reviews:', error);
    }
    return null;
  };

  // Google Maps and Places handlers
  const handlePlaceSelect = (place: any) => {
    setSelectedPlace(place);
  };

  const handleAddPlaceToAttractions = (place: any) => {
    setSelectedPlace(place);
    
    // Extract a photo if available
    let featured_image_url = null;
    const image_gallery: string[] = [];
    if (place.photos && place.photos.length > 0) {
      try {
        const apiKey =
          process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || process.env.GOOGLE_MAPS_API_KEY || "";
        // Handle both older getUrl and newer getURI methods from Google Places API
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

    setCreateAttractionData({
      name: place.name,
      description: place.editorial_summary?.overview || place.editorial_summary || '',
      attraction_type: getCategoryFromTypes(place.types),
      city: place.formatted_address?.split(',')[0] || '',
      address: place.formatted_address,
      google_place_id: place.place_id,
      google_maps_url: place.url,
      region: '',
      county: '',
      latitude: typeof place.geometry?.location?.lat === 'function' ? place.geometry.location.lat() : (place.geometry?.location?.lat || place.latitude || null),
      longitude: typeof place.geometry?.location?.lng === 'function' ? place.geometry.location.lng() : (place.geometry?.location?.lng || place.longitude || null),
      category_tags: place.types || [],
      host_personal_tip: '',
      host_favorite_time: '',
      host_insider_info: '',
      host_story: '',
      host_recommended_duration: '',
      opening_hours: place.opening_hours?.weekday_text ? {
        weekday_text: place.opening_hours.weekday_text
      } : {},
      admission_fee: place.price_level ? getPriceLevelText(place.price_level) : '',
      contact_info: {
        phone: place.formatted_phone_number || '',
        website: place.website || ''
      },
      difficulty_level: 'easy',
      duration_hours: null,
      group_size_recommendation: '',
      seasonal_availability: 'year_round',
      best_months: [],
      seasonal_notes: '',
      featured_image_url: featured_image_url,
      image_gallery: image_gallery
    });
    setShowCreateAttractionModal(true);
  };

  const getCategoryFromTypes = (types: string[]): string => {
    const typeMap: Record<string, string> = {
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

    for (const type of types) {
      if (typeMap[type]) {
        return typeMap[type];
      }
    }

    return 'cultural';
  };

  const getPriceLevelText = (level?: number): string => {
    if (!level) return 'Price not available';
    return '€'.repeat(level);
  };

  const statsCards = [
    {
      title: "Active Guest Groups",
      value: analytics?.guest_groups?.active ?? 0,
      description: "Groups currently exploring",
      icon: <Users className="h-5 w-5" />,
      trend: analytics?.guest_groups?.total !== null && analytics?.guest_groups?.total !== undefined ? `+${Math.floor(analytics.guest_groups.total * 0.12)}` : "+0",
      trendUp: true
    },
    {
      title: "Total Attractions",
      value: analytics?.attractions?.total ?? 0,
      description: "Local experiences shared",
      icon: <Landmark className="h-5 w-5" />,
      trend: analytics?.attractions?.total !== null && analytics?.attractions?.total !== undefined ? `+${Math.min(3, Math.floor(analytics.attractions.total * 0.1))}` : "+0",
      trendUp: true
    },
    {
      title: "Recommendations Given",
      value: analytics?.recommendations?.this_month ?? 0,
      description: "This month",
      icon: <Lightbulb className="h-5 w-5" />,
      trend: analytics?.recommendations?.this_month !== null && analytics?.recommendations?.this_month !== undefined ? `+${Math.floor(analytics.recommendations.this_month * 0.23)}%` : "+0%",
      trendUp: true
    },
    {
      title: "Guest Satisfaction",
      value: analytics?.satisfaction?.average_rating !== null && analytics?.satisfaction?.average_rating !== undefined ? `${analytics.satisfaction.average_rating}/5` : "0.0/5",
      description: "Average rating",
      icon: <Star className="h-5 w-5" />,
      trend: analytics?.satisfaction?.average_rating !== null && analytics?.satisfaction?.average_rating !== undefined ? `+${(analytics.satisfaction.average_rating - 4.6).toFixed(1)}` : "+0.0",
      trendUp: true
    }
  ];

  // Accommodation information for location-based analytics
  const resolvedPropertyCoordinates =
    isPlausibleGpsLatLng(profile?.latitude, profile?.longitude)
      ? { lat: Number(profile!.latitude), lng: Number(profile!.longitude) }
      : isPlausibleGpsLatLng(currentHost?.latitude, currentHost?.longitude)
        ? { lat: Number(currentHost!.latitude), lng: Number(currentHost!.longitude) }
        : undefined;

  const accommodationInfo = {
    property: {
      name: profile?.property_name || currentHost?.business_name || "Your Accommodation",
      type: profile?.property_type || currentHost?.business_type || "accommodation",
      location: {
        address: profile?.address || currentHost?.address || "Address not set",
        city: profile?.city || currentHost?.city || "City not set",
        county: profile?.county || currentHost?.county || "County not set",
        coordinates: resolvedPropertyCoordinates,
      },
      capacity: {
        maxGuests: profile?.max_guests || currentHost?.max_group_size || 0,
        rooms: profile?.number_of_rooms || 0
      }
    },
    services: {
      amenities: profile?.amenities || [],
      servicesOffered: profile?.services_offered || [],
      languages: currentHost?.languages || ["en"],
      specialties: profile?.expertise_areas || currentHost?.local_specialties || []
    },
    description: profile?.location_story || currentHost?.description || "No description available",
    welcomeMessage: currentHost?.welcome_message || `Welcome to ${profile?.city || currentHost?.city || 'our beautiful area'}!`
  };

  if (loading && !dashboardReady) {
    return (
      <div className="min-h-screen px-4 py-8 md:px-8">
        <div className="mx-auto max-w-7xl space-y-5">
          <div
            className="skeleton h-28 rounded-3xl"
            style={{ minHeight: "7rem", backgroundColor: "hsl(210 18% 92%)" }}
          />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="skeleton h-24 rounded-2xl"
                style={{ minHeight: "6rem", backgroundColor: "hsl(210 18% 92%)" }}
              />
            ))}
          </div>
          <div
            className="skeleton h-72 rounded-3xl"
            style={{ minHeight: "18rem", backgroundColor: "hsl(210 18% 92%)" }}
          />
          <p className="text-center text-sm text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-xl mb-4">⚠️</div>
          <p className="text-gray-600 mb-4">{error}</p>
          <Button onClick={loadDashboardData} variant="outline">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  // Show authentication required state if user is not authenticated
  if (!currentHost) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md mx-auto text-center bg-white p-8 rounded-lg shadow-lg border border-gray-200">
          <div className="mb-6 flex justify-center text-red-600">
            <Lock className="h-12 w-12" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Authentication Required</h1>
          <p className="text-gray-600 mb-6">
            You need to be logged in to access your dashboard. Please log in with your credentials.
          </p>

          {/* Development: Show dev login option */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800 mb-3">
                <strong>Development Mode:</strong> Use the test account for quick access
              </p>
              <Button
                onClick={devLogin}
                className="w-full bg-yellow-500 hover:bg-yellow-600 text-white"
              >
                <Wrench className="mr-2 h-4 w-4" />
                Dev Login (Test Account)
              </Button>
            </div>
          )}

          <div className="space-y-3">
            <Button
              onClick={() => window.location.href = '/login'}
              className="w-full"
              gradient
            >
              <LogIn className="mr-2 h-4 w-4" />
              Go to Login
            </Button>
            <Button
              variant="outline"
              onClick={() => window.location.reload()}
              className="w-full"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh Page
            </Button>
          </div>

          <div className="mt-6 text-xs text-gray-500">
            <p>If you continue to have issues, please:</p>
            <ul className="mt-2 space-y-1">
              <li>• Check your internet connection</li>
              <li>• Clear your browser&apos;s local storage</li>
              <li>• Contact support if the problem persists</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("min-h-screen", className)}>
      <AppLayout
        title={`Dobro dosli, ${currentHost?.full_name || profile?.business_name || "Host"}!`}
        subtitle={`Your Croatian hospitality dashboard • ${profile?.location || currentHost?.email || "No location yet"}`}
        navItems={[
          { id: "overview", label: "Overview", icon: <ChartNoAxesColumn /> },
          { id: "accommodation", label: "Stay", icon: <House /> },
          { id: "channels", label: "Channels", icon: <Link2 /> },
          { id: "groups", label: "Guests", icon: <Users /> },
          { id: "attractions", label: "Attractions", icon: <Landmark /> },
          { id: "routes", label: "Routes", icon: <Route /> },
          { id: "maintenance", label: "Maintenance", icon: <Wrench /> },
          { id: "adaptation", label: "Adaptation", icon: <Palette /> },
          { id: "map", label: "Map", icon: <Map /> },
          { id: "discover", label: "Discover", icon: <Search /> },
          { id: "cleaning", label: "Cleaning", icon: <Sparkles /> },
          { id: "insights", label: "Insights", icon: <Compass /> },
        ]}
        activeItem={activeTab}
        onSelectItem={(id) => setActiveTab(id as DashboardTab)}
        headerActions={
          <>
            {process.env.NODE_ENV === "development" && (
              <div className="rounded-2xl bg-muted px-3 py-2 text-xs text-muted-foreground">
                Auth: {currentHost ? "ok" : "missing"} • Token:{" "}
                {devTokenPresent === null ? "..." : devTokenPresent ? "present" : "missing"}
                {loading && dashboardReady ? " • refreshing…" : ""}
              </div>
            )}
            {!currentHost && (
              <Button variant="outline" onClick={devLogin}>
                Dev Login
              </Button>
            )}
            <Button variant="outline" onClick={logout}>
              Logout
            </Button>
          </>
        }
      >
        <HostDashboardMainContent
          activeTab={activeTab}
          statsCards={statsCards}
          guestGroups={guestGroups}
          realtimeUpdates={realtimeUpdates}
          loadDashboardData={loadDashboardData}
          accommodationInfo={accommodationInfo}
          setProfile={setProfile}
          profile={profile}
          onCreateGroup={() => setShowCreateGroupModal(true)}
          onViewGroup={(group) => {
            setSelectedGroup(group);
            setShowGroupDetailsModal(true);
          }}
          onCopyAccessCode={copyAccessCode}
          onRegenerateAccessCode={(id) => void handleRegenerateAccessCode(id)}
          regeneratingGroupId={regeneratingGroupId}
          attractions={attractions}
          openCreateAttractionModal={openCreateAttractionModal}
          openEditAttractionModal={openEditAttractionModal}
          openDeleteAttractionModal={openDeleteAttractionModal}
          openViewReviewsModal={openViewReviewsModal}
          openPhotoUploadModal={openPhotoUploadModal}
          viewMode={viewMode}
          onToggleViewMode={() => setViewMode(viewMode === "list" ? "map" : "list")}
          onPlaceSelect={handlePlaceSelect}
          onAddPlaceToAttractions={handleAddPlaceToAttractions}
          AccommodationTab={AccommodationTab}
        />
      </AppLayout>

      <HostDashboardModals
        showCreateGroupModal={showCreateGroupModal}
        setShowCreateGroupModal={setShowCreateGroupModal}
        showGroupDetailsModal={showGroupDetailsModal}
        setShowGroupDetailsModal={setShowGroupDetailsModal}
        selectedGroup={selectedGroup}
        copyAccessCode={copyAccessCode}
        onRegenerateAccessCode={(id) => void handleRegenerateAccessCode(id)}
        regeneratingGroupId={regeneratingGroupId}
        loadEVisitorData={loadEVisitorData}
        setShowEVisitorModal={setShowEVisitorModal}
        handleCreateGroup={handleCreateGroup}
        createGroupData={createGroupData}
        setCreateGroupData={setCreateGroupData}
        showCreateAttractionModal={showCreateAttractionModal}
        setShowCreateAttractionModal={setShowCreateAttractionModal}
        handleCreateAttraction={handleCreateAttraction}
        createAttractionData={createAttractionData as Record<string, unknown>}
        setCreateAttractionData={
          setCreateAttractionData as React.Dispatch<React.SetStateAction<Record<string, unknown>>>
        }
        selectedPlace={selectedPlace as unknown}
        showEditAttractionModal={showEditAttractionModal}
        selectedAttraction={selectedAttraction}
        setShowEditAttractionModal={setShowEditAttractionModal}
        handleEditAttraction={handleEditAttraction}
        showDeleteAttractionModal={showDeleteAttractionModal}
        setShowDeleteAttractionModal={setShowDeleteAttractionModal}
        handleDeleteAttraction={handleDeleteAttraction}
        showAnalyticsModal={showAnalyticsModal}
        setShowAnalyticsModal={setShowAnalyticsModal}
        showPhotoUploadModal={showPhotoUploadModal}
        setShowPhotoUploadModal={setShowPhotoUploadModal}
        handlePhotoUpload={handlePhotoUpload}
        showEVisitorModal={showEVisitorModal}
        evisitorData={evisitorData}
        setShowCreateEVisitorModal={setShowCreateEVisitorModal}
        setSelectedEVisitor={setSelectedEVisitor}
        setCreateEVisitorData={setCreateEVisitorData}
        handleDeleteEVisitor={handleDeleteEVisitor}
        handleMarkEVisitorRegistered={handleMarkEVisitorRegistered}
        showCreateEVisitorModal={showCreateEVisitorModal}
        showEditEVisitorModal={showEditEVisitorModal}
        setShowEditEVisitorModal={setShowEditEVisitorModal}
        handleUpdateEVisitor={handleUpdateEVisitor}
        handleCreateEVisitor={handleCreateEVisitor}
        createEVisitorData={createEVisitorData}
        hostProfileForGuestGroups={profile}
      />
    </div>
  );
};

const AccommodationTab: React.FC<{
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- nested API-shaped object; narrow when onboarding types land
  accommodationInfo: any;
  onRefresh: () => void;
  setProfile: React.Dispatch<React.SetStateAction<HostProfile | null>>;
  profile: HostProfile | null;
}> = ({ accommodationInfo, onRefresh, setProfile, profile }) => {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editData, setEditData] = React.useState(accommodationInfo);
  const [showAISuggestions, setShowAISuggestions] = React.useState(false);
  const [aiSuggestions, setAiSuggestions] = React.useState<any>(null);
  const [isGeneratingAI, setIsGeneratingAI] = React.useState(false);
  const [showRulesModal, setShowRulesModal] = React.useState(false);
  const [propertyRules, setPropertyRules] = React.useState({
    checkInTime: '15:00',
    checkOutTime: '11:00',
    cancellationPolicy: 'Flexible - Free cancellation up to 24 hours before arrival',
    houseRules: [
      'No smoking inside the property',
      'Quiet hours from 22:00 to 08:00',
      'Pets allowed with prior approval',
      'Maximum occupancy must not exceed booking'
    ],
    additionalPolicies: [
      'Early check-in available upon request (subject to availability)',
      'Late check-out available upon request (subject to availability)',
      'Security deposit may be required for certain bookings'
    ]
  });
  const [rulesModalBanner, setRulesModalBanner] = React.useState<string | null>(null);

  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const googleMapsBrowserKey =
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || process.env.GOOGLE_MAPS_API_KEY || "";

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    Array.from(files).forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setEditData((prev: typeof editData) => ({
          ...prev,
          gallery_images: [...(prev.gallery_images || []), reader.result as string],
        }));
      };
      reader.readAsDataURL(file);
    });
  };

  const removeImage = (indexToRemove: number) => {
    setEditData((prev: typeof editData) => ({
      ...prev,
      gallery_images: (prev.gallery_images || []).filter(
        (_: unknown, index: number) => index !== indexToRemove
      ),
    }));
  };

  React.useEffect(() => {
    try {
      if (typeof window === "undefined") return;
      const raw = localStorage.getItem("tg_property_rules_v1");
      if (!raw) return;
      const parsed = JSON.parse(raw) as typeof propertyRules;
      if (parsed && typeof parsed === "object") {
        setPropertyRules((prev) => ({
          ...prev,
          ...parsed,
          houseRules: Array.isArray(parsed.houseRules) ? parsed.houseRules : prev.houseRules,
          additionalPolicies: Array.isArray(parsed.additionalPolicies)
            ? parsed.additionalPolicies
            : prev.additionalPolicies,
        }));
      }
    } catch {
      /* ignore corrupt local data */
    }
  }, []);

  // Debug: Monitor accommodationInfo changes (only in development)
  React.useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log("AccommodationTab: accommodationInfo changed:", accommodationInfo);
      console.log("AccommodationTab: editData state:", editData);
      console.log("AccommodationTab: isEditing state:", isEditing);
    }
  }, [accommodationInfo, editData, isEditing]);

  const handleEdit = () => {
    // Map the complex accommodationInfo structure to the flat API structure
    const apiData = {
      property_name: accommodationInfo.property?.name || accommodationInfo.property_name || '',
      property_type: accommodationInfo.property?.type || accommodationInfo.property_type,
      max_guests: accommodationInfo.property?.capacity?.maxGuests || accommodationInfo.max_guests,
      number_of_rooms: accommodationInfo.property?.capacity?.rooms || accommodationInfo.number_of_rooms,
      amenities: accommodationInfo.services?.amenities || [],
      // Extract services_offered as a flat list from the nested services object
      services_offered: accommodationInfo.services?.servicesOffered || [],
      expertise_areas: accommodationInfo.services?.specialties || [],
      location_story: accommodationInfo.description || '',
      // Add location fields
      city: accommodationInfo.property?.location?.city || '',
      county: accommodationInfo.property?.location?.county || '',
      address: accommodationInfo.property?.location?.address || '',
      latitude: (() => {
        const c = accommodationInfo.property?.location?.coordinates;
        return c && isPlausibleGpsLatLng(c.lat, c.lng) ? c.lat : null;
      })(),
      longitude: (() => {
        const c = accommodationInfo.property?.location?.coordinates;
        return c && isPlausibleGpsLatLng(c.lat, c.lng) ? c.lng : null;
      })(),
      // Add languages and welcome message
      languages: accommodationInfo.services?.languages || ['hr', 'en'], // Default to Croatian and English
      welcome_message: accommodationInfo.welcomeMessage || '',
      gallery_images: accommodationInfo.gallery_images || profile?.gallery_images || []
    };

    console.log('✏️ Edit button clicked');
    console.log("Original accommodationInfo:", accommodationInfo);
    console.log("Mapped apiData:", apiData);

    setEditData(apiData);
    setIsEditing(true);
  };

  const handleSave = async () => {
    try {
      // Enhanced logging to debug the 422 error
      console.log("Attempting to save accommodation data:");
      console.log("editData object:", JSON.stringify(editData, null, 2));
      console.log("editData keys:", Object.keys(editData));
      console.log("editData values:", Object.values(editData));
      console.log("Current profile prop:", profile);
      console.log("Current accommodationInfo:", accommodationInfo);

      // Call API to save accommodation data
      const response = await hostsApi.updateProfile(editData);

      console.log("API Response:", response);
      console.log("API Response status:", response.success);
      console.log("API Response data:", response.data);
      console.log("API Response error:", response.error);

      if (response.success && response.data) {
        console.log('✅ Accommodation data saved successfully:', response.data);
        setIsEditing(false);

        // Update the local profile state immediately with the saved data
        if (response.data) {
          console.log("Updating profile state with new data...");
          setProfile((prevProfile) => {
            if (!prevProfile) return prevProfile;
            const updatedProfile = { ...prevProfile, ...response.data } as HostProfile;
            console.log("New profile state:", updatedProfile);
            return updatedProfile;
          });

        }

        // Refresh the dashboard data to ensure everything is in sync
        // This will update the accommodationInfo since it's derived from the profile
        console.log("Refreshing dashboard data...");
        onRefresh();

        // Show success message
        alert('Accommodation data saved successfully!');
      } else {
        console.error('❌ Failed to save accommodation data:');
        console.error('❌ Response error:', JSON.stringify(response.error, null, 2));
        console.error('❌ Full response:', JSON.stringify(response, null, 2));

        // Show more detailed error information
        let errorMessage = 'Failed to save accommodation data';
        if (response.error) {
          if (Array.isArray(response.error)) {
            errorMessage = `Validation errors: ${response.error
              .map((e: unknown) => {
                console.log("Individual error:", JSON.stringify(e, null, 2));
                if (e && typeof e === "object" && "message" in e) {
                  return String((e as { message?: unknown }).message ?? e);
                }
                return String(e);
              })
              .join(", ")}`;
          } else if (typeof response.error === "string") {
            errorMessage = response.error;
          } else if (
            typeof response.error === "object" &&
            response.error !== null &&
            "message" in response.error
          ) {
            errorMessage = String((response.error as { message?: unknown }).message);
          }
        }

        // You could add a toast notification here with errorMessage
        alert(`Error: ${errorMessage}`);
      }
    } catch (error) {
      console.error("Error saving accommodation data:", error);
      console.error("Error stack:", error instanceof Error ? error.stack : "No stack trace");
      alert(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleCancel = () => {
    // Reset editData to the original accommodationInfo structure
    const originalData = {
      property_name: accommodationInfo.property?.name || accommodationInfo.property_name || '',
      property_type: accommodationInfo.property?.type || accommodationInfo.property_type,
      max_guests: accommodationInfo.property?.capacity?.maxGuests || accommodationInfo.max_guests,
      number_of_rooms: accommodationInfo.property?.capacity?.rooms || accommodationInfo.number_of_rooms,
      amenities: accommodationInfo.services?.amenities || [],
      services_offered: accommodationInfo.services?.servicesOffered || [],
      expertise_areas: accommodationInfo.services?.specialties || [],
      location_story: accommodationInfo.description || '',
      city: accommodationInfo.property?.location?.city || '',
      county: accommodationInfo.property?.location?.county || '',
      address: accommodationInfo.property?.location?.address || '',
      latitude: (() => {
        const c = accommodationInfo.property?.location?.coordinates;
        return c && isPlausibleGpsLatLng(c.lat, c.lng) ? c.lat : null;
      })(),
      longitude: (() => {
        const c = accommodationInfo.property?.location?.coordinates;
        return c && isPlausibleGpsLatLng(c.lat, c.lng) ? c.lng : null;
      })(),
      languages: accommodationInfo.services?.languages || ['hr', 'en'], // Default to Croatian and English
      welcome_message: accommodationInfo.welcomeMessage || '',
      gallery_images: accommodationInfo.gallery_images || profile?.gallery_images || []
    };
    setEditData(originalData);
    setIsEditing(false);
  };

  const generateAISuggestions = async () => {
    setIsGeneratingAI(true);
    try {
      // Prepare current accommodation data for AI enhancement
      const currentData = {
        property_name: accommodationInfo.property?.name || accommodationInfo.property_name || '',
        property_type: accommodationInfo.property?.type || accommodationInfo.property_type || '',
        location_story: accommodationInfo.description || '',
        max_guests: accommodationInfo.property?.capacity?.maxGuests || accommodationInfo.max_guests || 0,
        number_of_rooms: accommodationInfo.property?.capacity?.rooms || accommodationInfo.number_of_rooms || 0,
        amenities: accommodationInfo.services?.amenities || [],
        services_offered: accommodationInfo.services?.servicesOffered || [],
        expertise_areas: accommodationInfo.services?.specialties || [],
        city: accommodationInfo.property?.location?.city || accommodationInfo.city || '',
        county: accommodationInfo.property?.location?.county || accommodationInfo.county || '',
        languages: accommodationInfo.services?.languages || ['hr', 'en']
      };

      // Call the AI enhancement API using the API client
      const response = await fetch(`${API_BASE_URL}/api/v1/onboarding/accommodation/ai-enhance`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': localStorage.getItem('session_token') || ''
        },
        body: JSON.stringify({
          current_data: currentData,
          enhancement_type: 'comprehensive'
        })
      });

      if (!response.ok) {
        throw new Error(`AI enhancement failed: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        setAiSuggestions({
          description: result.enhanced_content.description,
          amenities: result.enhanced_content.amenities,
          services: result.enhanced_content.services,
          specialties: result.enhanced_content.specialties,
          languages: result.enhanced_content.languages,
          welcomeMessage: result.enhanced_content.welcome_message
        });
        setShowAISuggestions(true);
      } else {
        throw new Error('AI enhancement failed to generate suggestions');
      }
    } catch (error) {
      console.error('Error generating AI suggestions:', error);
      // Fallback to basic enhancement if API fails
      const fallbackDescription = accommodationInfo.description ||
        `Experience authentic Croatian hospitality in this charming ${accommodationInfo.property?.type || 'property'} in ${accommodationInfo.property?.location?.city || 'Croatia'}. Perfect for guests seeking an authentic local experience with modern comforts.`;

      setAiSuggestions({
        description: fallbackDescription,
        amenities: ['air_conditioning', 'wifi', 'kitchen', 'parking'],
        services: ['guided_tours', 'airport_transfer', 'cleaning_service'],
        specialties: ['Local Culture', 'Gastronomy', 'Nature Exploration'],
        languages: ['hr', 'en'],
        welcomeMessage: "Dobro došli! Welcome to your Croatian home away from home."
      });
      setShowAISuggestions(true);
    } finally {
      setIsGeneratingAI(false);
    }
  };

  const applyAISuggestion = (field: string, value: any) => {
    setEditData((prev: typeof editData) => {
      const updated = { ...prev };

      switch (field) {
        case 'description':
          updated.location_story = value;
          break;
        case 'amenities':
          // Merge new amenities with existing ones, avoiding duplicates
          const existingAmenities = prev.amenities || [];
          const newAmenities = Array.isArray(value) ? value : [];
          updated.amenities = [...new Set([...existingAmenities, ...newAmenities])];
          break;
        case 'services':
          // Merge new services with existing ones, avoiding duplicates
          const existingServices = prev.services_offered || [];
          const newServices = Array.isArray(value) ? value : [];
          updated.services_offered = [...new Set([...existingServices, ...newServices])];
          break;
        case 'specialties':
          // Merge new specialties with existing ones, avoiding duplicates
          const existingSpecialties = prev.expertise_areas || [];
          const newSpecialties = Array.isArray(value) ? value : [];
          updated.expertise_areas = [...new Set([...existingSpecialties, ...newSpecialties])];
          break;
        case 'languages':
          // Merge new languages with existing ones, avoiding duplicates
          const existingLanguages = prev.languages || [];
          const newLanguages = Array.isArray(value) ? value : [];
          updated.languages = [...new Set([...existingLanguages, ...newLanguages])];
          break;
        case 'welcomeMessage':
          // Store welcome message in a custom field for later use
          updated.welcome_message = value;
          break;
        default:
          updated[field] = value;
      }

      return updated;
    });

    // Close the AI suggestions modal after applying
    setShowAISuggestions(false);
  };

  return (
    <div className="space-y-8">
      {/* Header with Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Accommodation Management</h2>
          <p className="text-gray-600">Manage your property details and enhance guest experiences</p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => {
              setRulesModalBanner(null);
              setShowRulesModal(true);
            }}
            className="flex items-center gap-2"
          >
            Property Rules
          </Button>
          <Button
            variant="outline"
            onClick={generateAISuggestions}
            disabled={isGeneratingAI}
            className="flex items-center gap-2"
          >
            {isGeneratingAI ? (
              <>
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                AI Thinking...
              </>
            ) : (
              <>
                AI Enhance
              </>
            )}
          </Button>
          {!isEditing ? (
            <Button onClick={handleEdit} className="flex items-center gap-2">
              ✏️ Edit Details
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleCancel}>
                Cancel
              </Button>
              <Button onClick={handleSave} className="flex items-center gap-2">
                Save Changes
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Accommodation Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="bg-gradient-to-br from-blue-50 to-indigo-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Property Details
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium text-gray-600">Property Name</p>
                {isEditing ? (
                  <input
                    type="text"
                    value={editData.property_name || ''}
                    onChange={(e) => setEditData((prev: typeof editData) => ({
                      ...prev,
                      property_name: e.target.value
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-lg font-semibold text-gray-900">{accommodationInfo.property?.name || accommodationInfo.property_name || 'Not set'}</p>
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Property Type</p>
                {isEditing ? (
                  <select
                    value={editData.property_type || ''}
                    onChange={(e) => setEditData((prev: typeof editData) => ({
                      ...prev,
                      property_type: e.target.value
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select type</option>
                    <option value="apartment">Apartment</option>
                    <option value="house">House</option>
                    <option value="villa">Villa</option>
                    <option value="room">Private Room</option>
                    <option value="cabin">Cabin</option>
                  </select>
                ) : (
                  <p className="text-gray-900 capitalize">{accommodationInfo.property?.type || accommodationInfo.property_type || 'Not set'}</p>
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Max Guests</p>
                {isEditing ? (
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={editData.max_guests || ''}
                    onChange={(e) => setEditData((prev: typeof editData) => ({
                      ...prev,
                      max_guests: parseInt(e.target.value) || 1
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-2xl font-bold text-blue-600">{accommodationInfo.property?.capacity?.maxGuests || accommodationInfo.max_guests || 'Not set'}</p>
                )}
              </div>
              {(accommodationInfo.property?.capacity?.rooms > 0 || accommodationInfo.number_of_rooms > 0) && (
                <div>
                  <p className="text-sm font-medium text-gray-600">Rooms</p>
                  {isEditing ? (
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={editData.number_of_rooms || ''}
                      onChange={(e) => setEditData((prev: typeof editData) => ({
                        ...prev,
                        number_of_rooms: parseInt(e.target.value) || 1
                      }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  ) : (
                    <p className="text-gray-900">{accommodationInfo.property?.capacity?.rooms || accommodationInfo.number_of_rooms || 'Not set'}</p>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-50 to-emerald-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Location
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium text-gray-600">City</p>
                {isEditing ? (
                  <input
                    type="text"
                    value={editData.city || ''}
                    onChange={(e) => setEditData((prev: typeof editData) => ({
                      ...prev,
                      city: e.target.value
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-lg font-semibold text-gray-900">{accommodationInfo.property?.location?.city || 'Not set'}</p>
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">County</p>
                {isEditing ? (
                  <input
                    type="text"
                    value={editData.county || ''}
                    onChange={(e) => setEditData((prev: typeof editData) => ({
                      ...prev,
                      county: e.target.value
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-gray-900">{accommodationInfo.property?.location?.county || 'Not set'}</p>
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Address</p>
                {isEditing ? (
                  <input
                    type="text"
                    value={editData.address || ''}
                    onChange={(e) => setEditData((prev: typeof editData) => ({
                      ...prev,
                      address: e.target.value
                    }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-sm text-gray-900">{accommodationInfo.property?.location?.address || 'Not set'}</p>
                )}
              </div>
              {(() => {
                const c = accommodationInfo.property?.location?.coordinates;
                const hasSavedGps = Boolean(c && isPlausibleGpsLatLng(c.lat, c.lng));
                return (
                  <div className="pt-2">
                    {hasSavedGps && !isEditing ? (
                      <>
                        <p className="text-sm font-medium text-green-600">✅ GPS Coordinates Set</p>
                        <p className="text-xs text-gray-500">
                          {Number(c!.lat).toFixed(4)}, {Number(c!.lng).toFixed(4)}
                        </p>
                      </>
                    ) : !isEditing ? (
                      <>
                        <p className="text-sm font-medium text-yellow-600">⚠️ GPS Needed</p>
                        <p className="text-xs text-gray-500">
                          Set latitude and longitude for distance calculations (use Edit, or complete map step in onboarding).
                        </p>
                      </>
                    ) : null}
                    {isEditing && (
                      <div className="mt-2 space-y-2">
                        <p className="text-xs font-medium text-gray-600">GPS coordinates (WGS84)</p>
                        <input
                          type="number"
                          step="0.0001"
                          placeholder="Latitude (e.g. 45.291)"
                          value={editData.latitude ?? ""}
                          onChange={(e) => {
                            const raw = e.target.value.trim();
                            const v = raw === "" ? NaN : parseFloat(raw);
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              latitude: raw === "" || !Number.isFinite(v) ? null : v,
                            }));
                          }}
                          className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                        />
                        <input
                          type="number"
                          step="0.0001"
                          placeholder="Longitude (e.g. 14.274)"
                          value={editData.longitude ?? ""}
                          onChange={(e) => {
                            const raw = e.target.value.trim();
                            const v = raw === "" ? NaN : parseFloat(raw);
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              longitude: raw === "" || !Number.isFinite(v) ? null : v,
                            }));
                          }}
                          className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                        />
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-50 to-pink-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Services
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium text-gray-600">Languages</p>
                <p className="text-gray-900">{accommodationInfo.services.languages.join(", ")}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Amenities</p>
                <p className="text-gray-900">{accommodationInfo.services.amenities.length} available</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Services</p>
                <p className="text-gray-900">{accommodationInfo.services.servicesOffered.length} offered</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Specialties</p>
                <p className="text-gray-900">{accommodationInfo.services.specialties.length} areas</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Information */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Amenities & Services */}
        <Card>
          <CardHeader>
            <CardTitle>Amenities & Services</CardTitle>
            <CardDescription>What your accommodation offers to guests</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Amenities */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Property Amenities</h4>
                {isEditing ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      {['wifi', 'parking', 'kitchen', 'balcony', 'air_conditioning', 'tv', 'washing_machine', 'garden'].map((amenity) => (
                        <label key={amenity} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100">
                          <input
                            type="checkbox"
                            checked={editData.amenities?.includes(amenity) || false}
                            onChange={(e) => {
                              setEditData((prev: typeof editData) => {
                                const currentAmenities = prev.amenities || [];
                                if (e.target.checked) {
                                  return { ...prev, amenities: [...currentAmenities, amenity] };
                                } else {
                                  return { ...prev, amenities: currentAmenities.filter((a: string) => a !== amenity) };
                                }
                              });
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-700 capitalize">{amenity.replace(/_/g, ' ')}</span>
                        </label>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Add custom amenity"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                            const newAmenity = e.currentTarget.value.trim();
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              amenities: [...(prev.amenities || []), newAmenity]
                            }));
                            e.currentTarget.value = '';
                          }
                        }}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                          if (input.value.trim()) {
                            const newAmenity = input.value.trim();
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              amenities: [...(prev.amenities || []), newAmenity]
                            }));
                            input.value = '';
                          }
                        }}
                      >
                        Add
                      </Button>
                    </div>
                  </div>
                ) : (
                  accommodationInfo.services.amenities.length > 0 ? (
                    <div className="grid grid-cols-2 gap-2">
                      {accommodationInfo.services.amenities.map((amenity: string, index: number) => (
                        <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                          <span className="text-green-500">✓</span>
                          <span className="text-sm text-gray-700 capitalize">{amenity.replace(/_/g, ' ')}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No amenities listed yet</p>
                  )
                )}
              </div>

              {/* Services */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Services Offered</h4>
                {isEditing ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      {['airport_transfer', 'guided_tours', 'cleaning_service', 'breakfast', 'laundry_service', 'bike_rental', 'car_rental', 'shuttle_service'].map((service) => (
                        <label key={service} className="flex items-center gap-2 p-2 bg-blue-50 rounded-lg cursor-pointer hover:bg-blue-100">
                          <input
                            type="checkbox"
                            checked={editData.services_offered?.includes(service) || false}
                            onChange={(e) => {
                              setEditData((prev: typeof editData) => {
                                const currentServices = prev.services_offered || [];
                                if (e.target.checked) {
                                  return { ...prev, services_offered: [...currentServices, service] };
                                } else {
                                  return { ...prev, services_offered: currentServices.filter((s: string) => s !== service) };
                                }
                              });
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-700 capitalize">{service.replace(/_/g, ' ')}</span>
                        </label>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Add custom service"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                            const newService = e.currentTarget.value.trim();
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              services_offered: [...(prev.services_offered || []), newService]
                            }));
                            e.currentTarget.value = '';
                          }
                        }}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                          if (input.value.trim()) {
                            const newService = input.value.trim();
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              services_offered: [...(prev.services_offered || []), newService]
                            }));
                            input.value = '';
                          }
                        }}
                      >
                        Add
                      </Button>
                    </div>
                  </div>
                ) : (
                  accommodationInfo.services.servicesOffered.length > 0 ? (
                    <div className="grid grid-cols-2 gap-2">
                      {accommodationInfo.services.servicesOffered.map((service: string, index: number) => (
                        <div key={index} className="flex items-center gap-2 p-2 bg-blue-50 rounded-lg">
                          <span className="text-blue-500">Info</span>
                          <span className="text-sm text-gray-700 capitalize">{service.replace(/_/g, ' ')}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No services listed yet</p>
                  )
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Local Expertise */}
        <Card>
          <CardHeader>
            <CardTitle>Local Expertise</CardTitle>
            <CardDescription>Your knowledge and specialties</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Languages */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Languages Spoken</h4>
                {isEditing ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      {['hr', 'en', 'de', 'it', 'fr', 'es'].map((lang) => (
                        <label key={lang} className="flex items-center gap-2 p-2 bg-blue-50 rounded-lg cursor-pointer hover:bg-blue-100">
                          <input
                            type="checkbox"
                            checked={editData.languages?.includes(lang) || false}
                            onChange={(e) => {
                              setEditData((prev: typeof editData) => {
                                const currentLanguages = prev.languages || [];
                                if (e.target.checked) {
                                  return { ...prev, languages: [...currentLanguages, lang] };
                                } else {
                                  return { ...prev, languages: currentLanguages.filter((l: string) => l !== lang) };
                                }
                              });
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-700">
                            {lang === 'hr' ? 'Croatian' : lang === 'en' ? 'English' : lang === 'de' ? 'German' : lang === 'it' ? 'Italian' : lang === 'fr' ? 'French' : lang === 'es' ? 'Spanish' : lang}
                          </span>
                        </label>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Add custom language (e.g., 'ru' for Russian)"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                            const newLang = e.currentTarget.value.trim();
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              languages: [...(prev.languages || []), newLang]
                            }));
                            e.currentTarget.value = '';
                          }
                        }}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                          if (input.value.trim()) {
                            const newLang = input.value.trim();
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              languages: [...(prev.languages || []), newLang]
                            }));
                            input.value = '';
                          }
                        }}
                      >
                        Add
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {accommodationInfo.services.languages.map((lang: string, index: number) => (
                      <span key={index} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                        {lang === 'hr' ? 'Croatian' : lang === 'en' ? 'English' : lang === 'de' ? 'German' : lang === 'it' ? 'Italian' : lang}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Specialties */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Local Specialties</h4>
                {isEditing ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      {['local_history', 'wine_tourism', 'nature_exploration', 'gastronomy', 'cultural_tours', 'adventure_sports', 'wellness', 'photography'].map((specialty) => (
                        <label key={specialty} className="flex items-center gap-2 p-2 bg-purple-50 rounded-lg cursor-pointer hover:bg-purple-100">
                          <input
                            type="checkbox"
                            checked={editData.expertise_areas?.includes(specialty) || false}
                            onChange={(e) => {
                              setEditData((prev: typeof editData) => {
                                const currentSpecialties = prev.expertise_areas || [];
                                if (e.target.checked) {
                                  return { ...prev, expertise_areas: [...currentSpecialties, specialty] };
                                } else {
                                  return { ...prev, expertise_areas: currentSpecialties.filter((s: string) => s !== specialty) };
                                }
                              });
                            }}
                            className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                          />
                          <span className="text-sm text-gray-700 capitalize">{specialty.replace(/_/g, ' ')}</span>
                        </label>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Add custom specialty"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                            const newSpecialty = e.currentTarget.value.trim();
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              expertise_areas: [...(prev.expertise_areas || []), newSpecialty]
                            }));
                            e.currentTarget.value = '';
                          }
                        }}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                          if (input.value.trim()) {
                            const newSpecialty = input.value.trim();
                            setEditData((prev: typeof editData) => ({
                              ...prev,
                              expertise_areas: [...(prev.expertise_areas || []), newSpecialty]
                            }));
                            input.value = '';
                          }
                        }}
                      >
                        Add
                      </Button>
                    </div>
                  </div>
                ) : (
                  accommodationInfo.services.specialties.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {accommodationInfo.services.specialties.map((specialty: string, index: number) => (
                        <span key={index} className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm capitalize">
                          {specialty.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No specialties listed yet</p>
                  )
                )}
              </div>

              {/* Description */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Property Description</h4>
                {isEditing ? (
                  <textarea
                    value={editData.location_story || ''}
                    onChange={(e) => setEditData((prev: typeof editData) => ({
                      ...prev,
                      location_story: e.target.value
                    }))}
                    placeholder="Describe your property and what makes it special..."
                    rows={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  accommodationInfo.description ? (
                    <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                      {accommodationInfo.description}
                    </p>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No description yet</p>
                  )
                )}
              </div>

              {/* Welcome Message */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Welcome Message</h4>
                {isEditing ? (
                  <input
                    type="text"
                    value={editData.welcome_message || ''}
                    onChange={(e) => setEditData((prev: typeof editData) => ({
                      ...prev,
                      welcome_message: e.target.value
                    }))}
                    placeholder="Enter a warm welcome message for your guests..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  accommodationInfo.welcomeMessage ? (
                    <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded-lg italic">
                      {`"${accommodationInfo.welcomeMessage}"`}
                    </p>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No welcome message yet</p>
                  )
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Images and Map section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Property Images</CardTitle>
            <CardDescription>Manage photos of your accommodation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center mb-4">
                <h4 className="font-medium text-gray-900">Current Photos</h4>
                {isEditing && (
                  <>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleImageUpload}
                      accept="image/*"
                      multiple
                      className="hidden"
                    />
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="flex items-center gap-2"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Plus className="h-4 w-4" /> Add Photos
                    </Button>
                  </>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {(editData.gallery_images || []).map((imgUrl: string, index: number) => (
                  <div key={index} className="aspect-square relative rounded-md overflow-hidden bg-gray-100 group">
                    <img 
                      src={imgUrl} 
                      alt={`Property photo ${index + 1}`} 
                      className="object-cover w-full h-full"
                    />
                    {isEditing && (
                      <div className="absolute inset-0 bg-black bg-opacity-40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <Button
                          size="sm"
                          variant="danger"
                          className="h-8 w-8 min-h-0 p-0 rounded-full"
                          onClick={() => removeImage(index)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
                {(!editData.gallery_images || editData.gallery_images.length === 0) && (
                  <div className="col-span-full py-8 text-center text-gray-500 border-2 border-dashed border-gray-200 rounded-md">
                    No photos uploaded yet. {isEditing && "Click 'Add Photos' to upload."}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Map View</CardTitle>
            <CardDescription>Property location on map</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full bg-gray-100 rounded-md overflow-hidden relative">
              {(() => {
                const mc = accommodationInfo.property?.location?.coordinates;
                return mc && isPlausibleGpsLatLng(mc.lat, mc.lng);
              })() ? (
                <iframe
                  width="100%"
                  height="100%"
                  style={{ border: 0 }}
                  loading="lazy"
                  allowFullScreen
                  referrerPolicy="no-referrer-when-downgrade"
                  src={
                    googleMapsBrowserKey
                      ? `https://www.google.com/maps/embed/v1/place?key=${encodeURIComponent(googleMapsBrowserKey)}&q=${accommodationInfo.property.location.coordinates.lat},${accommodationInfo.property.location.coordinates.lng}&zoom=14`
                      : `https://www.google.com/maps?q=${accommodationInfo.property.location.coordinates.lat},${accommodationInfo.property.location.coordinates.lng}&z=14&output=embed`
                  }
                ></iframe>
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500">
                  <MapPin className="h-8 w-8 mb-2 opacity-50" />
                  <p>No coordinates set</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Location Analytics Preview */}
      <Card className="bg-gradient-to-br from-yellow-50 to-orange-50">
        <CardHeader>
          <CardTitle>Location Analytics Preview</CardTitle>
          <CardDescription>How your location enables personalized recommendations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="mb-2 flex justify-center">
                <MapPin className="h-7 w-7 text-amber-600" />
              </div>
              <h4 className="font-medium text-gray-900 mb-2">Distance Calculations</h4>
              <p className="text-sm text-gray-600">
                {accommodationInfo.property?.location?.coordinates &&
                isPlausibleGpsLatLng(
                  accommodationInfo.property.location.coordinates.lat,
                  accommodationInfo.property.location.coordinates.lng
                )
                  ? "GPS coordinates enable accurate distance calculations to attractions"
                  : "Set GPS coordinates to enable distance-based recommendations"}
              </p>
            </div>
            <div className="text-center">
              <div className="mb-2 flex justify-center">
                <Target className="h-7 w-7 text-amber-600" />
              </div>
              <h4 className="font-medium text-gray-900 mb-2">Local Focus</h4>
              <p className="text-sm text-gray-600">
                Recommendations prioritized for {accommodationInfo.property.location.city} and {accommodationInfo.property.location.county} area
              </p>
            </div>
            <div className="text-center">
              <div className="mb-2 flex justify-center">
                <CarFront className="h-7 w-7 text-amber-600" />
              </div>
              <h4 className="font-medium text-gray-900 mb-2">Travel Planning</h4>
              <p className="text-sm text-gray-600">
                Guests can plan day trips based on proximity to your accommodation
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI Suggestions Modal */}
      {showAISuggestions && aiSuggestions && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">AI Enhancement Suggestions</h2>
              <Button variant="ghost" onClick={() => setShowAISuggestions(false)}>✕</Button>
            </div>

            {/* Context Section - Show what's being enhanced */}
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">Enhancing Your Existing Data</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-medium text-blue-800">Property Details:</p>
                  <p className="text-blue-700">
                    {accommodationInfo.property?.name || accommodationInfo.property_name || 'Not set'} •
                    {accommodationInfo.property?.type || accommodationInfo.property_type || 'Not set'} •
                    {accommodationInfo.property?.capacity?.maxGuests || accommodationInfo.max_guests || 'Not set'} guests
                  </p>
                </div>
                <div>
                  <p className="font-medium text-blue-800">Current Description:</p>
                  <p className="text-blue-700">
                    {accommodationInfo.description ?
                      `${accommodationInfo.description.substring(0, 100)}${accommodationInfo.description.length > 100 ? '...' : ''}` :
                      'No description yet'
                    }
                  </p>
                </div>
                <div>
                  <p className="font-medium text-blue-800">Existing Amenities:</p>
                  <p className="text-blue-700">
                    {accommodationInfo.services?.amenities?.length > 0 ?
                      accommodationInfo.services.amenities.slice(0, 3).join(', ') +
                      (accommodationInfo.services.amenities.length > 3 ? '...' : '') :
                      'None specified'
                    }
                  </p>
                </div>
                <div>
                  <p className="font-medium text-blue-800">Current Languages:</p>
                  <p className="text-blue-700">
                    {accommodationInfo.services?.languages?.length > 0 ?
                      accommodationInfo.services.languages.map((lang: string) =>
                        lang === 'hr' ? 'Croatian' : lang === 'en' ? 'English' : lang === 'de' ? 'German' : lang === 'it' ? 'Italian' : lang
                      ).join(', ') :
                      'None specified'
                    }
                  </p>
                </div>
                <div>
                  <p className="font-medium text-blue-800">Location:</p>
                  <p className="text-blue-700">
                    {accommodationInfo.property?.location?.city || accommodationInfo.city || 'Not set'},
                    {accommodationInfo.property?.location?.county || accommodationInfo.county || 'Croatia'}
                  </p>
                </div>
              </div>
              <p className="text-blue-600 text-xs mt-3">
                AI is building upon your existing information to create richer, more engaging content that reflects your property&apos;s unique characteristics.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Description Enhancement */}
              <Card>
                <CardHeader>
                  <CardTitle>Enhanced Description</CardTitle>
                  <CardDescription>AI-generated property description</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-700 mb-4">{aiSuggestions.description}</p>
                  <Button
                    size="sm"
                    onClick={() => applyAISuggestion('description', aiSuggestions.description)}
                    className="w-full"
                  >
                    Apply This Description
                  </Button>
                </CardContent>
              </Card>

              {/* Amenities Enhancement */}
              <Card>
                <CardHeader>
                  <CardTitle>Enhanced Amenities</CardTitle>
                  <CardDescription>AI-suggested property amenities</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {aiSuggestions.amenities.map((amenity: string, index: number) => (
                      <span key={index} className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs">
                        {amenity.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                  <Button
                    size="sm"
                    onClick={() => applyAISuggestion('amenities', aiSuggestions.amenities)}
                    className="w-full"
                  >
                    Apply These Amenities
                  </Button>
                </CardContent>
              </Card>

              {/* Services Enhancement */}
              <Card>
                <CardHeader>
                  <CardTitle>Enhanced Services</CardTitle>
                  <CardDescription>AI-suggested services</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {aiSuggestions.services.map((service: string, index: number) => (
                      <span key={index} className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                        {service.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                  <Button
                    size="sm"
                    onClick={() => applyAISuggestion('services', aiSuggestions.services)}
                    className="w-full"
                  >
                    Apply These Services
                  </Button>
                </CardContent>
              </Card>

              {/* Specialties Enhancement */}
              <Card>
                <CardHeader>
                  <CardTitle>Enhanced Specialties</CardTitle>
                  <CardDescription>AI-suggested local specialties</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {aiSuggestions.specialties.map((specialty: string, index: number) => (
                      <span key={index} className="px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs">
                        {specialty}
                      </span>
                    ))}
                  </div>
                  <Button
                    size="sm"
                    onClick={() => applyAISuggestion('specialties', aiSuggestions.specialties)}
                    className="w-full"
                  >
                    Apply These Specialties
                  </Button>
                </CardContent>
              </Card>

              {/* Languages Enhancement */}
              <Card>
                <CardHeader>
                  <CardTitle>Enhanced Languages</CardTitle>
                  <CardDescription>AI-suggested languages to offer</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {aiSuggestions.languages?.map((lang: string, index: number) => (
                      <span key={index} className="px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-xs">
                        {lang === 'hr' ? 'Croatian' : lang === 'en' ? 'English' : lang === 'de' ? 'German' : lang === 'it' ? 'Italian' : lang === 'fr' ? 'French' : lang === 'es' ? 'Spanish' : lang}
                      </span>
                    ))}
                  </div>
                  <Button
                    size="sm"
                    onClick={() => applyAISuggestion('languages', aiSuggestions.languages)}
                    className="w-full"
                  >
                    Apply These Languages
                  </Button>
                </CardContent>
              </Card>

              {/* Welcome Message Enhancement */}
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Enhanced Welcome Message</CardTitle>
                  <CardDescription>AI-generated personalized welcome message</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-700 mb-4 italic">{`"${aiSuggestions.welcomeMessage}"`}</p>
                  <Button
                    size="sm"
                    onClick={() => applyAISuggestion('welcomeMessage', aiSuggestions.welcomeMessage)}
                    className="w-full"
                  >
                    Apply This Welcome Message
                  </Button>
                </CardContent>
              </Card>
            </div>

            <div className="mt-6 flex justify-end">
              <Button onClick={() => setShowAISuggestions(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Property Rules Modal */}
      {showRulesModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Property Rules & Policies</h2>
              <Button
                variant="ghost"
                onClick={() => {
                  setRulesModalBanner(null);
                  setShowRulesModal(false);
                }}
              >
                ✕
              </Button>
            </div>

            {rulesModalBanner && (
              <p
                className="mb-4 rounded-md bg-blue-50 p-3 text-sm text-blue-900"
                role="status"
              >
                {rulesModalBanner}
              </p>
            )}

            <div className="space-y-6">
              {/* Check-in/Check-out Times */}
              <Card>
                <CardHeader>
                  <CardTitle>Check-in & Check-out Times</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Check-in Time</label>
                      <input
                        type="time"
                        value={propertyRules.checkInTime}
                        onChange={(e) => setPropertyRules(prev => ({ ...prev, checkInTime: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Check-out Time</label>
                      <input
                        type="time"
                        value={propertyRules.checkOutTime}
                        onChange={(e) => setPropertyRules(prev => ({ ...prev, checkOutTime: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Cancellation Policy */}
              <Card>
                <CardHeader>
                  <CardTitle>Cancellation Policy</CardTitle>
                </CardHeader>
                <CardContent>
                  <textarea
                    value={propertyRules.cancellationPolicy}
                    onChange={(e) => setPropertyRules(prev => ({ ...prev, cancellationPolicy: e.target.value }))}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Describe your cancellation policy..."
                  />
                </CardContent>
              </Card>

              {/* House Rules */}
              <Card>
                <CardHeader>
                  <CardTitle>House Rules</CardTitle>
                  <CardDescription>Rules that guests must follow during their stay</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {propertyRules.houseRules.map((rule, index) => (
                      <div key={index} className="flex items-center gap-3">
                        <input
                          type="text"
                          value={rule}
                          onChange={(e) => {
                            const newRules = [...propertyRules.houseRules];
                            newRules[index] = e.target.value;
                            setPropertyRules(prev => ({ ...prev, houseRules: newRules }));
                          }}
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                        />
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            const newRules = propertyRules.houseRules.filter((_, i) => i !== index);
                            setPropertyRules(prev => ({ ...prev, houseRules: newRules }));
                          }}
                          className="text-red-600 hover:text-red-700"
                        >
                          ✕
                        </Button>
                      </div>
                    ))}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setPropertyRules(prev => ({
                        ...prev,
                        houseRules: [...prev.houseRules, 'New rule...']
                      }))}
                      className="w-full"
                    >
                      + Add Rule
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Additional Policies */}
              <Card>
                <CardHeader>
                  <CardTitle>Additional Policies</CardTitle>
                  <CardDescription>Other important policies and information</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {propertyRules.additionalPolicies.map((policy, index) => (
                      <div key={index} className="flex items-center gap-3">
                        <input
                          type="text"
                          value={policy}
                          onChange={(e) => {
                            const newPolicies = [...propertyRules.additionalPolicies];
                            newPolicies[index] = e.target.value;
                            setPropertyRules(prev => ({ ...prev, additionalPolicies: newPolicies }));
                          }}
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                        />
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            const newPolicies = propertyRules.additionalPolicies.filter((_, i) => i !== index);
                            setPropertyRules(prev => ({ ...prev, additionalPolicies: newPolicies }));
                          }}
                          className="text-red-600 hover:text-red-700"
                        >
                          ✕
                        </Button>
                      </div>
                    ))}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setPropertyRules(prev => ({
                        ...prev,
                        additionalPolicies: [...prev.additionalPolicies, 'New policy...']
                      }))}
                      className="w-full"
                    >
                      + Add Policy
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* AI Enhancement for Rules */}
              <Card className="bg-gradient-to-br from-blue-50 to-purple-50">
                <CardHeader>
                  <CardTitle>AI Rules Enhancement</CardTitle>
                  <CardDescription>Let AI suggest comprehensive rules based on your property type and location</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <p className="text-sm text-gray-600">
                      AI can help you create comprehensive house rules, cancellation policies, and additional policies
                      that are appropriate for your property type and Croatian hospitality standards.
                    </p>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setPropertyRules((prev) => ({
                          ...prev,
                          houseRules: [
                            ...prev.houseRules,
                            "Sort waste per local municipality recycling rules",
                            "Register guests when required under Croatian tourist-stay regulations",
                          ].filter((r, i, a) => a.indexOf(r) === i),
                        }));
                        setRulesModalBanner(
                          "Added starter rules common for Croatian hosts. Edit the list, then save — full AI generation will use your property profile when the API is extended."
                        );
                      }}
                      className="w-full"
                    >
                      Generate AI-Enhanced Rules
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setRulesModalBanner(null);
                  setShowRulesModal(false);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={() => {
                  try {
                    if (typeof window !== "undefined") {
                      localStorage.setItem(
                        "tg_property_rules_v1",
                        JSON.stringify(propertyRules)
                      );
                    }
                    setRulesModalBanner(
                      "Rules saved on this device. Sync to your guest-facing profile when the host API adds a rules field."
                    );
                  } catch {
                    setRulesModalBanner("Could not save rules to browser storage.");
                  }
                }}
              >
                Save Rules
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


