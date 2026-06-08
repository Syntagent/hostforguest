"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { cn, isPlausibleGpsLatLng } from "@/lib/utils";
import {
  ChartNoAxesColumn,
  Compass,
  House,
  Landmark,
  Lightbulb,
  Link2,
  Lock,
  LogIn,
  LogOut,
  Map,
  MapPin,
  RefreshCw,
  Search,
  Sparkles,
  Star,
  Users,
  Wrench,
  Route,
  Palette,
  Scale,
} from "lucide-react";
import { hostsApi, guestGroupsApi, attractionsApi, complianceApi, HostProfile, GuestGroup, Attraction, GuestEVisitorData, GuestEVisitorDataCreate, API_BASE_URL } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { useToast } from "@/components/ui/toast";
import type { CreateGroupFormData, DashboardAnalytics } from "./dashboard-types";
import {
  dateInputToCheckInIso,
  dateInputToCheckOutIso,
  defaultStayDateStrings,
  validateStayDates,
} from "./guest-group-stay";
import { AppLayout } from "@/components/layout/app-layout";
import { HostDashboardMainContent } from "./widgets/host-dashboard-main-content";
import { HostDashboardModals } from "./modals/host-dashboard-modals";
import type { DashboardTab } from "./dashboard-tabs";
import { useDashboardTabUrl } from "./use-dashboard-tab-url";
import { useSearchParams } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { isHostProfileReady } from "@/lib/host-account-procedure";
import { AccommodationTab as AccommodationAgentTab } from "./accommodation-tab";

interface HostDashboardProps {
  className?: string;
}

export const HostDashboard: React.FC<HostDashboardProps> = ({ className }) => {
  const { user: currentHost, logout } = useAuth();
  const { showToast } = useToast();
  const [profile, setProfile] = useState<HostProfile | null>(null);
  const [guestGroups, setGuestGroups] = useState<GuestGroup[]>([]);
  const [attractions, setAttractions] = useState<Attraction[]>([]);
  const [realtimeUpdates, setRealtimeUpdates] = useState<Array<{ id: string; title: string; content: string; description?: string; created_at: string }>>([]);
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  /** After first successful load cycle, never swap the whole page for a skeleton (avoids "blank" UI while refresh runs). */
  const [dashboardReady, setDashboardReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { activeTab, selectTab } = useDashboardTabUrl();
  const searchParams = useSearchParams();
  const [complianceProgress, setComplianceProgress] = React.useState<{
    done: number;
    total_relevant: number;
    percent: number;
  } | null>(null);
  const profileReady = useMemo(
    () => isHostProfileReady(profile, currentHost),
    [profile, currentHost]
  );

  // Guest Groups state
  const [showCreateGroupModal, setShowCreateGroupModal] = useState(false);
  const [showGroupDetailsModal, setShowGroupDetailsModal] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<GuestGroup | null>(null);
  const [regeneratingGroupId, setRegeneratingGroupId] = useState<string | null>(null);
  const [deletingGroupId, setDeletingGroupId] = useState<string | null>(null);
  const [createGroupData, setCreateGroupData] = useState<CreateGroupFormData>(() => ({
    group_name: '',
    group_size: 2,
    ...defaultStayDateStrings(),
    preferences: [{
      guest_name: '',
      age_range: 'adult',
      interests: [],
      mobility_level: 'high',
      budget_level: 'medium',
      language_preference: 'en'
    }]
  }));

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

  useEffect(() => {
    if (!currentHost?.id) return;
    loadDashboardData();
  }, [currentHost?.id]);

  useEffect(() => {
    if (searchParams.get("open") === "evisitor" && activeTab === "groups") {
      showToast({
        type: "info",
        title: "eVisitor",
        message: "Otvorite grupu gostiju i upravljajte eVisitor podacima u detaljima grupe.",
      });
    }
  }, [searchParams, activeTab, showToast]);

  const loadDashboardData = async (refresh = false) => {
    setLoading(true);
    setError(null);

    try {
      if (!currentHost) {
        console.error('No authenticated user found');
        setError('Authentication required. Please log in again.');
        return;
      }

      const bundle = await hostsApi.getDashboardStats(refresh);
      if (bundle.status === 401) {
        logout();
        return;
      }
      if (bundle.success && bundle.data) {
        const d = bundle.data;
        if (d.analytics) setAnalytics(d.analytics as DashboardAnalytics);
        if (d.profile) setProfile(d.profile as HostProfile);
        if (d.guest_groups) setGuestGroups(d.guest_groups);
        if (d.attractions) setAttractions(d.attractions);
        if (d.realtime_updates) setRealtimeUpdates(d.realtime_updates);
      } else {
        setError(bundle.error || "Failed to load dashboard data.");
      }

      const complianceRes = await complianceApi.getMe();
      if (complianceRes.success && complianceRes.data?.progress) {
        setComplianceProgress(complianceRes.data.progress);
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
    const group_name = createGroupData.group_name?.trim();
    if (!group_name) {
      showToast({
        type: "warning",
        title: "Group name required",
        message: "Add a name before creating the guest group.",
      });
      return;
    }
    const stayErr = validateStayDates(
      createGroupData.check_in_date,
      createGroupData.check_out_date
    );
    if (stayErr) {
      showToast({
        type: "warning",
        title: "Stay dates required",
        message: stayErr,
      });
      return;
    }
    try {
      const response = await guestGroupsApi.create({
        group_name,
        group_size: createGroupData.group_size,
        check_in_date: dateInputToCheckInIso(createGroupData.check_in_date),
        check_out_date: dateInputToCheckOutIso(createGroupData.check_out_date),
      });
      if (response.success && response.data) {
        setGuestGroups([...guestGroups, response.data]);
        setShowCreateGroupModal(false);
        setCreateGroupData({
          group_name: '',
          group_size: 2,
          ...defaultStayDateStrings(),
          preferences: [{
            guest_name: '',
            age_range: 'adult',
            interests: [],
            mobility_level: 'high',
            budget_level: 'medium',
            language_preference: 'en'
          }]
        });
        showToast({
          type: "success",
          title: "Guest group saved",
          message: `"${response.data.group_name}" was created successfully.`,
        });
        await loadDashboardData();
        return;
      }
      if (response.status === 401) {
        showToast({ type: "error", title: "Session expired", message: "Please log in again." });
        logout();
        return;
      }
      showToast({
        type: "error",
        title: "Could not save group",
        message: response.error || "Please check the group name and try again.",
      });
    } catch (error) {
      console.error('Error creating guest group:', error);
      showToast({
        type: "error",
        title: "Network error",
        message: "Could not reach the server while creating the guest group.",
      });
    }
  };

  const copyAccessCode = (accessCode: string) => {
    const text = String(accessCode ?? "").trim();
    if (!text) {
      showToast({
        type: "warning",
        title: "No access code yet",
        message: "Open View Details or generate a new code from the group actions.",
      });
      return;
    }
    void (async () => {
      try {
        await navigator.clipboard.writeText(text);
        showToast({
          type: "success",
          title: "Access code copied",
          message: "The code is ready to paste for your guest.",
        });
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
            showToast({
              type: "success",
              title: "Access code copied",
              message: "The code is ready to paste for your guest.",
            });
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
        showToast({
          type: "error",
          title: "Could not generate code",
          message: res.error || "Check that the API is running the latest version.",
        });
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
        showToast({
          type: "error",
          title: "Missing access code",
          message: "The API responded without a code. Check POST /regenerate-code.",
        });
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
      showToast({
        type: clipboardOk ? "success" : "info",
        title: clipboardOk ? "Access code copied" : "New access code",
        message: clipboardOk ? code : `Copy manually: ${code}`,
        duration: 7000,
      });
    } catch (e) {
      console.error(e);
      showToast({
        type: "error",
        title: "Could not generate code",
        message: "Try again after the API finishes loading.",
      });
    } finally {
      setRegeneratingGroupId(null);
    }
  };

  const handleDeleteGroup = async (group: GuestGroup) => {
    const label = group.group_name?.trim() || "this group";
    if (
      typeof window !== "undefined" &&
      !window.confirm(`Delete "${label}"? This cannot be undone.`)
    ) {
      return;
    }
    setDeletingGroupId(String(group.id));
    try {
      const res = await guestGroupsApi.delete(String(group.id));
      if (!res.success && res.status !== 204) {
        showToast({
          type: "error",
          title: "Could not delete group",
          message: res.error || "Try again in a moment.",
        });
        return;
      }
      setGuestGroups((prev) => prev.filter((g) => String(g.id) !== String(group.id)));
      setSelectedGroup((prev) =>
        prev && String(prev.id) === String(group.id) ? null : prev
      );
      if (showGroupDetailsModal && selectedGroup?.id === group.id) {
        setShowGroupDetailsModal(false);
      }
      showToast({
        type: "success",
        title: "Group deleted",
        message: `"${label}" was removed.`,
      });
    } catch (e) {
      console.error(e);
      showToast({
        type: "error",
        title: "Could not delete group",
        message: "Try again in a moment.",
      });
    } finally {
      setDeletingGroupId(null);
    }
  };

  const emptyAttractionForm = () => ({
    name: '',
    description: '',
    attraction_type: 'cultural',
    city: '',
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
    opening_hours: {} as Record<string, unknown>,
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
    google_maps_url: null as string | null,
  });

  const mergeAttractionFormPayload = (payload?: Record<string, unknown>) => ({
    ...createAttractionData,
    ...(payload ?? {}),
  });

  const validateAttractionForm = (data: typeof createAttractionData): string | null => {
    if (
      !data.name?.trim() ||
      !data.description?.trim() ||
      !data.attraction_type?.trim() ||
      !data.city?.trim()
    ) {
      return 'Please fill in all required fields (name, description, attraction type, city)';
    }
    const hasCoords =
      typeof data.latitude === 'number' && typeof data.longitude === 'number';
    const hasAddressForGeo = Boolean(data.address?.trim() && data.city?.trim());
    if (!hasCoords && !hasAddressForGeo) {
      return 'Please add geolocation (pick a place on the map or enter address and city)';
    }
    return null;
  };

  // Attraction handlers (modal passes fresh payload; React state may still be stale)
  const handleCreateAttraction = async (payload?: Record<string, unknown>) => {
    const formData = mergeAttractionFormPayload(payload);
    setCreateAttractionData(formData);

    try {
      if (!currentHost) {
        const message = 'Authentication required. Please log in again.';
        setError(message);
        throw new Error(message);
      }

      const validationError = validateAttractionForm(formData);
      if (validationError) {
        setError(validationError);
        showToast({ type: 'warning', title: 'Missing fields', message: validationError });
        throw new Error(validationError);
      }

      const response = await attractionsApi.create(formData);
      if (response.success && response.data) {
        setAttractions([...attractions, response.data]);
        setShowCreateAttractionModal(false);
        setSelectedPlace(null);
        setCreateAttractionData(emptyAttractionForm());
        await loadDashboardData();
        showToast({ type: 'success', title: 'Attraction saved', message: response.data.name });
        return;
      }
      if (response.status === 401) {
        logout();
        throw new Error('Session expired');
      }
      const message =
        response.status === 422
          ? `Validation error: ${response.error}`
          : `Failed to create attraction: ${response.error}`;
      setError(message);
      showToast({ type: 'error', title: 'Could not save attraction', message });
      throw new Error(message);
    } catch (error) {
      if (error instanceof Error && error.message.startsWith('Please ')) {
        throw error;
      }
      if (error instanceof Error && (error.message === 'Session expired' || error.message.startsWith('Validation') || error.message.startsWith('Failed to create'))) {
        throw error;
      }
      console.error('Error creating attraction:', error);
      const message = 'Network error occurred while creating attraction';
      setError(message);
      showToast({ type: 'error', title: 'Could not save attraction', message });
      throw new Error(message);
    }
  };

  const handleEditAttraction = async (payload?: Record<string, unknown>) => {
    if (!selectedAttraction) return;

    const formData = mergeAttractionFormPayload(payload);
    setCreateAttractionData(formData);

    try {
      if (!currentHost) {
        const message = 'Authentication required. Please log in again.';
        setError(message);
        throw new Error(message);
      }

      const validationError = validateAttractionForm(formData);
      if (validationError) {
        setError(validationError);
        showToast({ type: 'warning', title: 'Missing fields', message: validationError });
        throw new Error(validationError);
      }

      const response = await attractionsApi.update(selectedAttraction.id, formData);
      if (response.success && response.data) {
        setAttractions(attractions.map(attraction =>
          attraction.id === selectedAttraction.id ? response.data! : attraction
        ));
        setShowEditAttractionModal(false);
        setSelectedAttraction(null);
        setSelectedPlace(null);
        setCreateAttractionData(emptyAttractionForm());
        await loadDashboardData();
        showToast({ type: 'success', title: 'Attraction updated', message: response.data.name });
        return;
      }
      if (response.status === 401) {
        logout();
        throw new Error('Session expired');
      }
      const message =
        response.status === 422
          ? `Validation error: ${response.error}`
          : `Failed to update attraction: ${response.error}`;
      setError(message);
      showToast({ type: 'error', title: 'Could not update attraction', message });
      throw new Error(message);
    } catch (error) {
      if (error instanceof Error && (
        error.message.startsWith('Please ') ||
        error.message === 'Session expired' ||
        error.message.startsWith('Validation') ||
        error.message.startsWith('Failed to update')
      )) {
        throw error;
      }
      console.error('Error updating attraction:', error);
      const message = 'Network error occurred while updating attraction';
      setError(message);
      showToast({ type: 'error', title: 'Could not update attraction', message });
      throw new Error(message);
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

  const averageRating = analytics?.satisfaction?.average_rating ?? 0;
  const totalReviews = analytics?.satisfaction?.total_reviews ?? 0;
  const ratingDelta = averageRating - 4.6;
  const formattedRatingDelta =
    ratingDelta === 0 ? "0.0" : `${ratingDelta > 0 ? "+" : ""}${ratingDelta.toFixed(1)}`;
  const activeGuestGroups = analytics?.guest_groups?.active ?? 0;
  const totalGuestGroups = analytics?.guest_groups?.total ?? 0;
  const totalAttractions = analytics?.attractions?.total ?? 0;
  const recommendationsThisMonth = analytics?.recommendations?.this_month ?? 0;

  const statsCards = [
    {
      title: "Active Guest Groups",
      value: activeGuestGroups,
      description: "Groups in stay today (by dates)",
      icon: <Users className="h-5 w-5" />,
      href: "/dashboard?tab=groups",
      trend: totalGuestGroups > 0 ? `+${Math.floor(totalGuestGroups * 0.12)}` : undefined,
      trendUp: true
    },
    {
      title: "Total Attractions",
      value: totalAttractions,
      description: "Local experiences shared",
      icon: <Landmark className="h-5 w-5" />,
      href: "/dashboard?tab=attractions",
      trend: totalAttractions > 0 ? `+${Math.min(3, Math.floor(totalAttractions * 0.1))}` : undefined,
      trendUp: true
    },
    {
      title: "Recommendations Given",
      value: recommendationsThisMonth,
      description: "This month",
      icon: <Lightbulb className="h-5 w-5" />,
      href: "/dashboard?tab=insights",
      trend: recommendationsThisMonth > 0 ? `+${Math.floor(recommendationsThisMonth * 0.23)}%` : undefined,
      trendUp: true
    },
    {
      title: "Guest Satisfaction",
      value: totalReviews > 0 ? `${averageRating}/5` : "No ratings",
      description: totalReviews > 0 ? `${totalReviews} guest review${totalReviews === 1 ? "" : "s"}` : "Awaiting guest reviews",
      icon: <Star className="h-5 w-5" />,
      href: "/dashboard?tab=insights",
      trend: totalReviews > 0 ? formattedRatingDelta : undefined,
      trendUp: ratingDelta >= 0
    },
    ...(complianceProgress
      ? [
          {
            title: "Compliance",
            value: `${complianceProgress.done}/${complianceProgress.total_relevant}`,
            description: `${complianceProgress.percent}% done — state obligations`,
            icon: <Scale className="h-5 w-5" />,
            href: "/dashboard?tab=compliance",
            trend: undefined,
            trendUp: true,
          },
        ]
      : []),
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
          <Button onClick={() => void loadDashboardData(true)} variant="outline">
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
        title={currentHost?.full_name || profile?.business_name || "Host"}
        subtitle={`Your Croatian hospitality dashboard • ${profile?.location || currentHost?.email || "No location yet"}`}
        navItems={[
          { id: "overview", label: "Overview", icon: <ChartNoAxesColumn /> },
          { id: "accommodation", label: "Accommodation", icon: <House /> },
          { id: "channels", label: "Channels", icon: <Link2 /> },
          { id: "compliance", label: "Compliance", icon: <Scale /> },
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
        onSelectItem={(id) => selectTab(id as DashboardTab)}
        headerActions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={logout}
              className="h-8 w-8 min-h-0 rounded-xl p-0 sm:h-auto sm:w-auto sm:min-h-10 sm:px-4"
              aria-label="Logout"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:ml-1 sm:inline">Logout</span>
            </Button>
          </>
        }
      >
        {dashboardReady && !profileReady && (
          <Alert className="mx-4 mb-4 border-amber-200 bg-amber-50 text-amber-950 sm:mx-5">
            <AlertTitle>Property profile incomplete</AlertTitle>
            <AlertDescription>
              Your account is signed in, but guests need a completed property profile (location,
              stay details).{" "}
              <Link href="/onboarding?from=login" className="font-medium underline">
                Complete onboarding
              </Link>{" "}
              to unlock the full dashboard.
            </AlertDescription>
          </Alert>
        )}
        <HostDashboardMainContent
          activeTab={activeTab}
          hostName={currentHost?.full_name || profile?.business_name || "Host"}
          statsCards={statsCards}
          guestGroups={guestGroups}
          realtimeUpdates={realtimeUpdates}
          loadDashboardData={loadDashboardData}
          dashboardLoading={loading && dashboardReady}
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
          onDeleteGroup={(g) => void handleDeleteGroup(g)}
          deletingGroupId={deletingGroupId}
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
          AccommodationTab={AccommodationAgentTab}
          onNavigateTab={(tab, extraQuery) => selectTab(tab, extraQuery)}
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
        onGuestGroupUpdated={(updated) => {
          setGuestGroups((prev) =>
            prev.map((g) => (String(g.id) === String(updated.id) ? { ...g, ...updated } : g))
          );
          setSelectedGroup((prev) =>
            prev && String(prev.id) === String(updated.id) ? { ...prev, ...updated } : prev
          );
        }}
        onDeleteGroup={(g) => void handleDeleteGroup(g)}
        deletingGroupId={deletingGroupId}
      />
    </div>
  );
};
