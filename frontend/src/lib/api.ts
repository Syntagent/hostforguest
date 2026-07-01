// API Client for TouristGuideLocal Backend
function resolveApiBaseUrl(): string {
  // Browser dev: always use same-origin `/api/*` proxy (avoids CORS when UI is 127.0.0.1:3055
  // but .env points at http://localhost:8000).
  if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
    return "";
  }
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (typeof raw === "string" && raw.trim() !== "") {
    return raw.replace(/\/$/, "");
  }
  if (process.env.NODE_ENV === "development") {
    return "";
  }
  return "http://localhost:8000".replace(/\/$/, "");
}

export const API_BASE_URL = resolveApiBaseUrl();

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  status?: number;
}

function formatApiErrorPayload(data: unknown): string {
  if (!data || typeof data !== "object") return "Request failed";
  const d = data as { detail?: unknown };
  const detail = d.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((x: { msg?: string; type?: string }) => x?.msg || JSON.stringify(x))
      .filter(Boolean)
      .join("; ");
  }
  return "Request failed";
}

function formatNetworkError(error: unknown): string {
  if (error instanceof TypeError) {
    return "Cannot reach API server. Check backend on port 8000 and NEXT_PUBLIC_API_URL.";
  }
  if (error instanceof Error && error.message) {
    return `Network error: ${error.message}`;
  }
  return "Network error";
}

class ApiClient {
  private baseURL: string;
  private sessionToken: string | null = null;
  private refreshToken: string | null = null;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
    if (typeof window !== 'undefined') {
      this.sessionToken = localStorage.getItem('session_token');
      this.refreshToken = localStorage.getItem('refresh_token');
    }
  }

  setSessionTokens(sessionToken: string | null, refreshToken: string | null) {
    this.sessionToken = sessionToken;
    this.refreshToken = refreshToken;
    if (typeof window !== 'undefined') {
      if (sessionToken) {
        localStorage.setItem('session_token', sessionToken);
      } else {
        localStorage.removeItem('session_token');
      }
      if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken);
      } else {
        localStorage.removeItem('refresh_token');
      }
    }
  }

  /**
   * Re-read tokens from localStorage when in-memory copy is empty (HMR, race after redirect, etc.).
   */
  private hydrateSessionFromStorage(): void {
    if (typeof window === "undefined") return;
    if (!this.sessionToken) {
      const s = localStorage.getItem("session_token");
      const r = localStorage.getItem("refresh_token");
      if (s) {
        this.sessionToken = s;
        this.refreshToken = r;
      }
    }
  }

  private resolveEndpointFromRedirect(location: string, requestUrl: string): string | null {
    if (!location) return null;
    try {
      const resolved = new URL(location, requestUrl);
      const base = new URL(this.baseURL || requestUrl);
      if (resolved.origin !== base.origin) {
        return `${resolved.pathname}${resolved.search}`;
      }
      const basePath = base.pathname.replace(/\/$/, "");
      let path = resolved.pathname;
      if (basePath && path.startsWith(basePath)) {
        path = path.slice(basePath.length) || "/";
      }
      return `${path}${resolved.search}`;
    } catch {
      return location.startsWith("/") ? location : null;
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    redirectRetry = false
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;

    this.hydrateSessionFromStorage();

    // Add session token to headers if available
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    const extra = options.headers;
    if (extra && typeof extra === "object" && !(extra instanceof Headers)) {
      Object.assign(headers, extra as Record<string, string>);
    }

    if (this.sessionToken) {
      headers['X-Session-Token'] = this.sessionToken;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        redirect: redirectRetry ? "follow" : "manual",
      });

      if (
        !redirectRetry &&
        (response.status === 307 || response.status === 308)
      ) {
        const nextEndpoint = this.resolveEndpointFromRedirect(
          response.headers.get("Location") ?? "",
          url
        );
        if (nextEndpoint) {
          return this.request(nextEndpoint, options, true);
        }
      }

      const rawText = await response.text();
      let data: unknown = {};
      if (rawText) {
        try {
          data = JSON.parse(rawText) as unknown;
        } catch {
          data = {};
        }
      }

      if (!response.ok) {
        // Handle session expiration
        if (response.status === 401 && this.refreshToken) {
          const refreshResult = await this.refreshSession();
          if (refreshResult) {
            // Retry the original request with new token
            return this.request(endpoint, options);
          }
        }

        return {
          success: false,
          error: formatApiErrorPayload(data),
          status: response.status,
        };
      }

      return {
        success: true,
        data: data as T,
        status: response.status,
      };
    } catch (error) {
      if (process.env.NODE_ENV === "development") {
        console.warn("API request failed:", endpoint, error);
      }
      return {
        success: false,
        error: formatNetworkError(error),
        status: 0,
      };
    }
  }

  private async refreshSession(): Promise<boolean> {
    this.hydrateSessionFromStorage();
    if (!this.refreshToken) {
      return false;
    }

    try {
      const response = await fetch(`${this.baseURL}/api/v1/hosts/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });

      const rawText = await response.text();
      let data: { session_token?: string } = {};
      if (rawText) {
        try {
          data = JSON.parse(rawText) as { session_token?: string };
        } catch {
          data = {};
        }
      }

      if (response.ok && typeof data.session_token === "string") {
        this.setSessionTokens(data.session_token, this.refreshToken);
        return true;
      }
      this.setSessionTokens(null, null);
      return false;
    } catch (error) {
      console.error('Session refresh failed:', error);
      this.setSessionTokens(null, null);
      return false;
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// API Types
export interface Host {
  id: string;
  email: string;
  full_name: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  created_at: string;
  profile?: HostProfile;
  address?: string;
  city?: string;
  county?: string;
  business_name?: string;
  business_type?: string;
  latitude?: number | null;
  longitude?: number | null;
  max_group_size?: number;
  languages?: string[];
  local_specialties?: string[];
  description?: string;
  welcome_message?: string;
  /** When API returns a contact phone for the host account */
  phone?: string | null;
}

/** Map /hosts/me and /hosts/login host JSON to a consistent Host (full_name + coordinates). */
export function normalizeHostFromApi(raw: unknown): Host | null {
  if (!raw || typeof raw !== "object") return null;
  const h = raw as Record<string, unknown>;
  const id = h.id != null ? String(h.id) : "";
  if (!id) return null;

  const first = typeof h.first_name === "string" ? h.first_name : "";
  const last = typeof h.last_name === "string" ? h.last_name : "";
  let fullName = typeof h.full_name === "string" ? h.full_name.trim() : "";
  if (!fullName) fullName = `${first} ${last}`.trim();
  if (!fullName) fullName = "Host";

  const numOrNull = (v: unknown): number | null => {
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string" && v.trim()) {
      const n = parseFloat(v);
      return Number.isFinite(n) ? n : null;
    }
    return null;
  };

  return {
    id,
    email: String(h.email ?? ""),
    full_name: fullName,
    first_name: first || undefined,
    last_name: last || undefined,
    is_active: Boolean(h.is_active ?? true),
    created_at:
      typeof h.created_at === "string" ? h.created_at : String(h.created_at ?? ""),
    profile: h.profile as HostProfile | undefined,
    address: typeof h.address === "string" ? h.address : undefined,
    city: typeof h.city === "string" ? h.city : undefined,
    county: typeof h.county === "string" ? h.county : undefined,
    business_name: typeof h.business_name === "string" ? h.business_name : undefined,
    business_type: typeof h.business_type === "string" ? h.business_type : undefined,
    latitude: numOrNull(h.latitude),
    longitude: numOrNull(h.longitude),
    max_group_size: typeof h.max_group_size === "number" ? h.max_group_size : undefined,
    languages: Array.isArray(h.languages) ? (h.languages as string[]) : undefined,
    local_specialties: Array.isArray(h.local_specialties)
      ? (h.local_specialties as string[])
      : undefined,
    description: typeof h.description === "string" ? h.description : undefined,
    welcome_message:
      typeof h.welcome_message === "string" ? h.welcome_message : undefined,
    phone:
      typeof h.phone === "string"
        ? h.phone
        : h.phone === null
          ? null
          : undefined,
  };
}

export interface HostProfile {
  id: string;
  host_id: string;
  property_name?: string;
  property_type?: string;
  number_of_rooms?: number;
  max_guests?: number;
  city?: string;
  county?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  services_offered?: string[];
  amenities?: string[];
  expertise_areas?: string[];
  favorite_local_spots?: string[];
  trusted_partners?: Record<string, unknown>[];
  special_offers?: Record<string, unknown>[];
  seasonal_recommendations?: Record<string, unknown>;
  availability_calendar?: Record<string, unknown>;
  typical_guest_profile?: Record<string, unknown>;
  success_stories?: string[];
  profile_image_url?: string;
  gallery_images?: string[];
  social_media_links?: Record<string, string>;
  guest_testimonials?: string[];
  location_story?: string;
  google_verified?: boolean;
  onboarding_completed?: boolean;
  onboarding_completed_at?: string;
  ai_generated_content?: boolean;
  created_at?: string;
  updated_at?: string;
  // Legacy fields kept for backward compatibility
  business_name?: string;
  business_description?: string;
  location?: string;
  coordinates?: [number, number];
  specialties?: string[];
  languages?: string[];
  welcome_message?: string;
  host_story?: string;
  local_tips?: string[];
}

export type AccommodationChecklistStatus = "missing" | "in_progress" | "draft" | "done" | "skipped";

export interface AccommodationChecklistItemState {
  id: string;
  status: AccommodationChecklistStatus;
  label?: string;
  notes?: string;
}

export interface AccommodationAgentMessage {
  role: "assistant" | "user" | "system";
  content: string;
}

export interface AccommodationPatch {
  property_name?: string;
  property_type?: string;
  max_guests?: number;
  number_of_rooms?: number;
  city?: string;
  county?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  location_story?: string;
  amenities?: string[];
  services_offered?: string[];
  expertise_areas?: string[];
  languages?: string[];
  welcome_message?: string;
  gallery_images?: string[];
}

export interface AccommodationAgentMessageRequest {
  message: string;
  focused_item_id?: string | null;
  checklist_state: AccommodationChecklistItemState[];
  accommodation_snapshot: Record<string, unknown>;
  conversation_history: AccommodationAgentMessage[];
}

export interface AccommodationAgentMessageResponse {
  success: boolean;
  reply: string;
  quick_replies: string[];
  suggested_patch: AccommodationPatch;
  suggestion_options: { id: string; label: string; patch: AccommodationPatch }[];
  checklist_updates: AccommodationChecklistItemState[];
  next_focus_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface AccommodationEnhancementResponse {
  success: boolean;
  enhancement_type: string;
  enhanced_content: {
    description?: string;
    amenities?: string[];
    services?: string[];
    specialties?: string[];
    languages?: string[];
    welcome_message?: string;
  };
  original_data?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

/** Accommodation row (host_profiles) linked to a guest group — same source as Accommodation tab. */
export interface GuestGroupAccommodation {
  host_profile_id: string;
  property_name?: string | null;
  property_type?: string | null;
  address?: string | null;
  city?: string | null;
  county?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface GuestGroup {
  id: string;
  host_id: string;
  /** FK to host_profiles.id; set when the group is created. */
  host_profile_id?: string | null;
  group_name: string;
  /** Present when the API includes it; use getHostGuestExperience for a reliable code + link. */
  access_code?: string;
  group_size: number;
  status: 'pending' | 'active' | 'completed';
  preferences?: GuestPreference[];
  created_at: string;
  check_in_date?: string | null;
  check_out_date?: string | null;
  /** Live property snapshot from host_profiles (dashboard + guest access responses). */
  accommodation?: GuestGroupAccommodation | null;
}

/** Response from GET /api/v1/guest-groups/{id}/guest-experience (host session). */
export interface HostGuestExperience {
  guest_group: GuestGroup & Record<string, unknown>;
  access_code: string | null;
  access_code_expires_at: string | null;
  guest_app_path: string;
  guest_join_path: string;
}

export interface GuestPreference {
  guest_name: string;
  age_range: string;
  interests: string[];
  mobility_level: string;
  budget_level: string;
  language_preference: string;
}

/** Full row from GET .../preferences (wizard + API fields). */
export interface GuestPreferenceRecord extends GuestPreference {
  id: string;
  guest_group_id: string;
  age_category?: string | null;
  personal_interests?: string[];
  dietary_needs?: string[];
  cultural_interests?: string[];
  food_interests?: string[];
  mobility_notes?: string | null;
  created_at: string;
  updated_at: string;
}

/** Host profile JSON: surfaced as `recommendations.attractions` in guest host-offerings. */
export interface HostFavoriteLocalSpot {
  name?: string;
  type?: string;
  description?: string;
  distance_km?: number;
  local_tip?: string;
  best_time?: string;
  difficulty?: string;
  specialty?: string;
  price_range?: string;
  facilities?: string;
}

/** Stored as JSON on host profile; shape may vary — UI tolerates strings or objects. */
export type GuestTestimonialEntry =
  | string
  | {
      quote?: string;
      text?: string;
      message?: string;
      body?: string;
      review?: string;
      content?: string;
      author?: string;
      name?: string;
      guest_name?: string;
      from?: string;
      by?: string;
      rating?: number;
    };

/** Host offerings for guests (guest-group access code). */
export interface GuestHostOfferingsPayload {
  /** Where guests actually stay (property), vs host business profile city. */
  stay_info?: {
    property_name?: string | null;
    address?: string | null;
    city?: string | null;
    region?: string | null;
    amenities?: string[];
    max_guests?: number | null;
  };
  host_info: {
    name: string;
    city?: string | null;
    /** When different from stay (e.g. registered city). */
    broader_city?: string | null;
    welcome_message: string;
    languages?: string[] | null;
    local_specialties?: string[];
    business_type?: string | null;
  };
  location_info: {
    city?: string | null;
    region?: string | null;
    coordinates?: { lat: number; lng: number } | null;
    verified_location?: boolean;
  };
  recommendations: {
    attractions: HostFavoriteLocalSpot[];
    expertise_areas: string[];
    local_tips: string[];
  };
  guest_services: {
    max_group_size?: number | null;
    typical_stay_duration?: number | null;
    supported_languages?: string[] | null;
    ai_powered?: boolean;
    personalized_recommendations?: boolean;
  };
  contact: {
    can_message_host?: boolean;
    response_time?: string;
    ai_assistant_available?: boolean;
  };
  metadata: {
    access_code?: string;
    last_updated?: string | null;
    profile_completed?: boolean;
  };
  profile_extras?: {
    property_name?: string | null;
    location_story?: string | null;
    guest_testimonials?: GuestTestimonialEntry[];
  };
}

export interface GuestHostOfferingsApiResponse {
  success: boolean;
  host_offerings: GuestHostOfferingsPayload;
  access_code: string;
  valid_access: boolean;
}

export interface GuestEVisitorData {
  id: string;
  guest_group_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  nationality: string;
  id_type: 'passport' | 'id_card';
  id_number: string;
  id_issuing_country: string;
  id_expiry_date?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  arrival_date: string;
  departure_date: string;
  email?: string;
  phone?: string;
  evisitor_registered: boolean;
  evisitor_registration_date?: string;
  evisitor_confirmation_number?: string;
  created_at: string;
  updated_at: string;
}

export interface GuestEVisitorDataCreate {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  nationality: string;
  id_type: 'passport' | 'id_card';
  id_number: string;
  id_issuing_country: string;
  id_expiry_date?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  arrival_date: string;
  departure_date: string;
  email?: string;
  phone?: string;
}

export interface GuestEVisitorDataUpdate {
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;
  nationality?: string;
  id_type?: 'passport' | 'id_card';
  id_number?: string;
  id_issuing_country?: string;
  id_expiry_date?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  arrival_date?: string;
  departure_date?: string;
  email?: string;
  phone?: string;
}

export interface Attraction {
  id: string;
  name: string;
  description: string;
  category: string;
  location: string;
  coordinates?: [number, number];
  opening_hours: Record<string, string>;
  cost_estimate: string;
  authenticity_level: string;
  seasonal_info: Record<string, any>;
  host_tips?: string[];
  average_rating?: number;
  review_count?: number;

  // Extended properties used in HostDashboard
  attraction_type?: string;
  city?: string;
  address?: string;
  region?: string;
  county?: string;
  latitude?: number | null;
  longitude?: number | null;
  category_tags?: string[];
  host_personal_tip?: string;
  host_favorite_time?: string;
  host_insider_info?: string;
  host_story?: string;
  host_recommended_duration?: string;
  admission_fee?: string;
  contact_info?: Record<string, string>;
  difficulty_level?: string;
  duration_hours?: number | null;
  group_size_recommendation?: string;
  seasonal_availability?: string;
  best_months?: number[];
  seasonal_notes?: string;
  featured_image_url?: string | null;
  image_gallery?: string[];
  google_place_id?: string | null;
  /** Optional Google Places–sourced fields used in host UI */
  rating?: number;
  user_ratings_total?: number;
  price_level?: number;
  website?: string;
  phone_number?: string;
}

/** Approved guest reviews from GET /attractions/{id}/reviews (public). */
export interface AttractionGuestReview {
  id: string;
  rating: number;
  title?: string | null;
  review_text?: string | null;
  visit_date?: string | null;
  pros?: string[];
  cons?: string[];
  tips_for_others?: string | null;
  response_from_host?: string | null;
  created_at: string;
}

export interface Recommendation {
  id: string;
  guest_group_id: string;
  attraction_id: string;
  score: number;
  reason: string;
  personalization_factors: string[];
  created_at: string;
  attraction?: Attraction;
  /** Present when the backend row has guest thumbs (1 or 5). */
  feedback_rating?: number | null;
}

/** Host / guest itinerary row from API */
export interface HostItineraryRow {
  id: string;
  guest_group_id: string | null;
  host_id: string;
  title: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  base_location: string;
  pace: string;
  budget_level: string;
  transportation_preference: string;
  language: string;
  status: string;
  is_template: boolean;
  total_days: number;
  completion_rate: number;
  guest_satisfaction: number | null;
  created_at: string;
  updated_at: string;
}

export interface ItineraryActivityDTO {
  id: string;
  day_plan_id: string;
  title: string;
  description?: string | null;
  activity_type: string;
  category?: string | null;
  location_name: string;
  scheduled_start_time: string;
  scheduled_end_time: string;
  estimated_duration: number;
  sequence_order: number;
  status: string;
  travel_time_minutes: number;
  travel_distance_km: number;
  attraction_id?: string | null;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  google_maps_url?: string | null;
  host_tip?: string | null;
  cost_per_person?: number | null;
  created_at?: string;
}

export interface DayPlanDTO {
  id: string;
  itinerary_id: string;
  day_number: number;
  date: string;
  title?: string | null;
  theme?: string | null;
  start_time?: string;
  end_time?: string;
  status: string;
  description?: string | null;
  host_tips?: string | null;
  estimated_duration?: number | null;
  total_distance?: number | null;
  total_travel_time?: number | null;
  estimated_cost?: number | null;
  completion_percentage?: number;
  created_at?: string;
  activities?: ItineraryActivityDTO[];
}

export interface ItineraryWithDetailsDTO extends HostItineraryRow {
  day_plans: DayPlanDTO[];
}

/** Guest-facing simplified shape (legacy) */
export interface Itinerary {
  id: string;
  guest_group_id: string;
  title: string;
  description: string;
  start_date: string;
  end_date: string;
  status: 'draft' | 'active' | 'completed';
  day_plans: DayPlan[];
}

export interface DayPlan {
  id: string;
  itinerary_id: string;
  day_number: number;
  theme?: string | null;
  activities: ItineraryActivity[];
  estimated_cost?: number | null;
  travel_info?: Record<string, unknown>;
  description?: string | null;
  host_tips?: string | null;
  total_distance?: number | null;
  total_travel_time?: number | null;
}

export interface ItineraryActivity {
  id: string;
  day_plan_id: string;
  attraction_id?: string | null;
  title?: string;
  description?: string | null;
  activity_type?: string;
  location_name?: string;
  address?: string | null;
  scheduled_start_time?: string;
  scheduled_end_time?: string;
  estimated_duration?: number;
  travel_time_minutes?: number;
  travel_distance_km?: number;
  cost_per_person?: number | null;
  google_maps_url?: string | null;
  host_tip?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  sequence_order?: number;
  status?: string;
  /** Legacy / display alias when API only returns scheduled_start_time */
  start_time?: string;
  duration_minutes?: number;
  notes?: string;
  attraction?: Attraction;
}

export interface ItineraryMapViewData {
  day_plan_id: string;
  locations: Array<{
    id: string;
    name: string;
    lat: number;
    lng: number;
    type: string;
    marker_color?: string;
    start_time?: string | null;
    sequence?: number;
  }>;
  route: { waypoints: string[]; optimize: boolean; mode: string };
  center: { lat: number; lng: number };
  zoom: number;
  bounds?: { north: number; south: number; east: number; west: number } | null;
}

export interface ItinerarySuggestionResponseDTO {
  suggested_itinerary: Record<string, unknown>;
  day_plans: Record<string, unknown>[];
  activities: Record<string, unknown>[];
  reasoning: string;
  alternatives: string[];
}

// API Methods
export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<{
      host: Host;
      session_token: string;
      refresh_token: string;
      expires_at: string;
      refresh_expires_at: string;
    }>('/api/v1/hosts/login', {
      email,
      password,
    }),

  register: (hostData: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    address: string;
    city: string;
  }) =>
    apiClient.post<Host>('/api/v1/hosts/register', hostData),

  getCurrentHost: () =>
    apiClient.get<Host>('/api/v1/hosts/me'),

  logout: () =>
    apiClient.post('/api/v1/hosts/logout'),

  refreshSession: (refreshToken: string) =>
    apiClient.post<{
      session_token: string;
      expires_at: string;
    }>('/api/v1/hosts/refresh', { refresh_token: refreshToken }),

  getSessions: () =>
    apiClient.get('/api/v1/hosts/sessions'),

  logoutAllDevices: () =>
    apiClient.post('/api/v1/hosts/logout-all'),
};

export const hostsApi = {
  getProfile: () =>
    apiClient.get<HostProfile>('/api/v1/hosts/me/profile'),

  updateProfile: (profileData: Partial<HostProfile>) =>
    apiClient.put<HostProfile>('/api/v1/hosts/me/profile', profileData),

  geocodeLocation: (params: { address?: string; city?: string; county?: string }) => {
    const qs = new URLSearchParams();
    if (params.address?.trim()) qs.set('address', params.address.trim());
    if (params.city?.trim()) qs.set('city', params.city.trim());
    if (params.county?.trim()) qs.set('county', params.county.trim());
    const query = qs.toString();
    return apiClient.get<{
      latitude: number;
      longitude: number;
      matched_query: string;
      precision: string;
    }>(`/api/v1/hosts/me/geocode${query ? `?${query}` : ''}`);
  },

  getDashboardStats: (refresh = false) =>
    apiClient.get<{
      analytics: Record<string, unknown>;
      profile: HostProfile | null;
      guest_groups: GuestGroup[];
      attractions: Attraction[];
      realtime_updates: Array<{
        id: string;
        title: string;
        content: string;
        description?: string;
        created_at: string | null;
      }>;
      cached_at: string;
    }>(`/api/v1/hosts/dashboard/stats${refresh ? '?refresh=true' : ''}`),

  getAnalytics: () =>
    apiClient.get<{
      guest_groups: {
        total: number;
        active: number;
        inactive: number;
      };
      attractions: {
        total: number;
        categories: Record<string, number>;
      };
      recommendations: {
        total_given: number;
        this_month: number;
      };
      satisfaction: {
        average_rating: number;
        total_reviews: number;
      };
    }>('/api/v1/hosts/analytics'),
};

export const guestGroupsApi = {
  create: (groupData: {
    group_name: string;
    group_size: number;
  }) =>
    apiClient.post<GuestGroup>('/api/v1/guest-groups/', groupData),

  getByHost: () =>
    apiClient.get<GuestGroup[]>('/api/v1/guest-groups/host'),

  getHostGuestExperience: (groupId: string) =>
    apiClient.get<HostGuestExperience>(
      `/api/v1/guest-groups/${groupId}/guest-experience`
    ),

  regenerateAccessCode: (groupId: string) =>
    apiClient.post<{
      id: string;
      code: string;
      status: string;
      guest_group_id: string;
      expires_at: string;
      usage_count: number;
      max_usage_count: number;
      created_at: string;
    }>(`/api/v1/guest-groups/${groupId}/regenerate-code`, {}),

  getByAccessCode: (accessCode: string) =>
    apiClient.get<GuestGroup>(`/api/v1/guest-groups/access/${accessCode}`),

  updatePreferences: (groupId: string, preferences: GuestPreference[]) =>
    apiClient.put<GuestGroup>(`/api/v1/guest-groups/${groupId}/preferences`, {
      preferences,
    }),

  // Guest Preference Management
  addGuestPreference: (accessCode: string, preferenceData: {
    guest_name: string;
    age_category: string;
    personal_interests: string[];
    dietary_needs: string[];
    cultural_interests: string[];
    food_interests: string[];
    language_preference: string;
    mobility_notes?: string | null;
  }) =>
    apiClient.post(`/api/v1/guest-groups/access/${accessCode}/preferences`, preferenceData),

  getGuestPreferences: (accessCode: string) =>
    apiClient.get<GuestPreferenceRecord[]>(`/api/v1/guest-groups/access/${accessCode}/preferences`),

  getHostOfferings: (accessCode: string) =>
    apiClient.get<GuestHostOfferingsApiResponse>(
      `/api/v1/guest-groups/access/${accessCode}/host-offerings`
    ),

  sendHostMessage: (
    accessCode: string,
    body: { message: string; type?: string; guest_name?: string }
  ) =>
    apiClient.post<{
      success: boolean;
      response_type?: string;
      message?: string;
      suggestions?: string[];
      estimated_response_time?: string;
    }>(`/api/v1/guest-groups/access/${accessCode}/host-message`, body),

  updateGuestPreference: (accessCode: string, preferenceId: string, preferenceData: any) =>
    apiClient.put(`/api/v1/guest-groups/access/${accessCode}/preferences/${preferenceId}`, preferenceData),

  deleteGuestPreference: (accessCode: string, preferenceId: string) =>
    apiClient.delete(`/api/v1/guest-groups/access/${accessCode}/preferences/${preferenceId}`),

  // E-Visitor Data Management
  getEVisitorData: (groupId: string) =>
    apiClient.get<GuestEVisitorData[]>(`/api/v1/guest-groups/${groupId}/evisitor-data`),

  createEVisitorData: (groupId: string, evisitorData: GuestEVisitorDataCreate) =>
    apiClient.post<GuestEVisitorData>(`/api/v1/guest-groups/${groupId}/evisitor-data`, evisitorData),

  updateEVisitorData: (groupId: string, evisitorId: string, evisitorData: GuestEVisitorDataUpdate) =>
    apiClient.put<GuestEVisitorData>(`/api/v1/guest-groups/${groupId}/evisitor-data/${evisitorId}`, evisitorData),

  deleteEVisitorData: (groupId: string, evisitorId: string) =>
    apiClient.delete(`/api/v1/guest-groups/${groupId}/evisitor-data/${evisitorId}`),

  markEVisitorRegistered: (groupId: string, evisitorId: string, confirmationNumber: string) =>
    apiClient.post<GuestEVisitorData>(`/api/v1/guest-groups/${groupId}/evisitor-data/${evisitorId}/register`, {
      confirmation_number: confirmationNumber,
    }),
};

export const attractionsApi = {
  getAll: (params?: {
    category?: string;
    location?: string;
    search?: string;
  }) =>
    apiClient.get<Attraction[]>(
      `/api/v1/attractions${params ? `?${new URLSearchParams(params).toString()}` : ''}`
    ),

  getById: (id: string) =>
    apiClient.get<Attraction>(`/api/v1/attractions/${id}`),

  getByHost: () =>
    apiClient.get<Attraction[]>('/api/v1/attractions/host'),

  enhanceAttraction: (aiRequest: unknown) =>
    apiClient.post<{
      enhanced_description: string;
      enhancement_method: string;
      ai_provider: string;
      context_used: unknown;
    }>("/api/v1/attractions/ai-enhance", aiRequest),

  create: (attractionData: Partial<Attraction>) =>
    apiClient.post<Attraction>('/api/v1/attractions', attractionData),

  update: (id: string, attractionData: Partial<Attraction>) =>
    apiClient.put<Attraction>(`/api/v1/attractions/${id}`, attractionData),

  delete: (id: string) =>
    apiClient.delete(`/api/v1/attractions/${id}`),

  getAnalytics: (id: string) =>
    apiClient.get<{
      views: number;
      recommendations: number;
      average_rating: number;
      review_count: number;
      guest_feedback: Array<{
        rating: number;
        comment: string;
        created_at: string;
      }>;
    }>(`/api/v1/attractions/${id}/analytics`),

  generateContent: (attractionData: {
    name: string;
    category?: string;
    location?: string;
    host_interests?: string[];
  }) =>
    apiClient.post<{
      success: boolean;
      content: Partial<Attraction>;
      data_source: string;
      sources_used: number;
      personalization_level: string;
    }>('/api/v1/attractions/generate-content', attractionData),

  /** Public list of approved reviews for guest detail UI (no auth). */
  getGuestReviews: (attractionId: string, opts?: { skip?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (opts?.skip != null) q.set("skip", String(opts.skip));
    if (opts?.limit != null) q.set("limit", String(opts.limit));
    const qs = q.toString();
    return apiClient.get<AttractionGuestReview[]>(
      `/api/v1/attractions/${encodeURIComponent(attractionId)}/reviews${qs ? `?${qs}` : ""}`
    );
  },
};



/** FastAPI returns a batch object; older clients may expect a bare array. */
type RecommendationBatchDTO = {
  recommendations: Recommendation[];
  total_count: number;
  generated_at?: string;
  guest_group_id?: string;
};

/** Raw guest recommendation row from API (enriched or legacy). */
type GuestRecommendationRaw = Recommendation & {
  relevance_score?: number;
  why_recommended?: string | null;
  title?: string;
};

function normalizeGuestRecommendation(
  raw: GuestRecommendationRaw,
  guestGroupId?: string
): Recommendation {
  const score =
    typeof raw.score === "number"
      ? raw.score
      : typeof raw.relevance_score === "number"
        ? raw.relevance_score
        : 0;
  const reason =
    (raw.reason && String(raw.reason).trim()) ||
    (raw.why_recommended && String(raw.why_recommended).trim()) ||
    (raw as { description?: string }).description?.trim() ||
    "";
  let attraction = raw.attraction;
  if (!attraction && raw.attraction_id) {
    const title = raw.title?.trim();
    attraction = {
      id: String(raw.attraction_id),
      name: title || "Place",
      description: (raw as { description?: string }).description?.trim() || "",
      category: "experience",
      location: "",
      opening_hours: {},
      cost_estimate: "",
      authenticity_level: "local",
      seasonal_info: {},
    };
  }
  return {
    id: String(raw.id),
    guest_group_id: String(raw.guest_group_id || guestGroupId || ""),
    attraction_id: String(raw.attraction_id || attraction?.id || ""),
    score,
    reason: reason || "Recommended for your stay.",
    personalization_factors: Array.isArray(raw.personalization_factors)
      ? raw.personalization_factors.map(String)
      : [],
    created_at: raw.created_at,
    attraction,
    feedback_rating: raw.feedback_rating ?? null,
  };
}

export const recommendationsApi = {
  getForGroup: async (accessCode: string) => {
    const res = await apiClient.post<Recommendation[] | RecommendationBatchDTO>(
      `/api/v1/recommendations/guest/${accessCode}`,
      {}
    );
    if (!res.success || res.data == null) {
      return res as ApiResponse<Recommendation[]>;
    }
    const d = res.data;
    const guestGroupId =
      !Array.isArray(d) && typeof d === "object" && d.guest_group_id
        ? String(d.guest_group_id)
        : undefined;
    const list = Array.isArray(d) ? d : (d as RecommendationBatchDTO).recommendations ?? [];
    const normalized = list.map((r) =>
      normalizeGuestRecommendation(r as GuestRecommendationRaw, guestGroupId)
    );
    return { ...res, data: normalized };
  },

  getHistory: async (accessCode: string) => {
    const res = await apiClient.get<GuestRecommendationRaw[]>(
      `/api/v1/recommendations/guest/${accessCode}/history`
    );
    if (!res.success || res.data == null) {
      return res as ApiResponse<Recommendation[]>;
    }
    return {
      ...res,
      data: res.data.map((r) => normalizeGuestRecommendation(r)),
    };
  },

  provideFeedback: (accessCode: string, feedback: {
    recommendation_id: string;
    rating: number;
    feedback_text?: string;
  }) =>
    apiClient.post(`/api/v1/recommendations/guest/${accessCode}/feedback`, feedback),
};

export const itinerariesApi = {
  getForGroup: (accessCode: string) =>
    apiClient.get<Itinerary>(`/api/v1/itineraries/guest/${accessCode}/itinerary`),

  /** List reusable route templates (host session). */
  getTemplates: () =>
    apiClient.get<HostItineraryRow[]>('/api/v1/itineraries/host/templates'),

  /** List guest itineraries, non-templates (host session). */
  getHostItineraries: () =>
    apiClient.get<HostItineraryRow[]>('/api/v1/itineraries/host/itineraries'),

  getById: (itineraryId: string, includeActivities = true) =>
    apiClient.get<ItineraryWithDetailsDTO>(
      `/api/v1/itineraries/${itineraryId}?include_activities=${includeActivities}`
    ),

  /**
   * Create guest itinerary (pass guestGroupId) or template (omit guestGroupId, body.is_template true).
   */
  createItinerary: (
    body: {
      title: string;
      description?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      base_location: string;
      pace?: string;
      budget_level?: string;
      transportation_preference?: string;
      language?: string;
      is_template?: boolean;
      group_interests?: string[];
      mobility_considerations?: string[];
      weather_backup_plans?: boolean;
      shared_with_guests?: boolean;
      allows_guest_modifications?: boolean;
      voting_enabled?: boolean;
    },
    guestGroupId?: string | null
  ) => {
    const q =
      guestGroupId && !body.is_template
        ? `?guest_group_id=${encodeURIComponent(guestGroupId)}`
        : '';
    return apiClient.post<HostItineraryRow>(`/api/v1/itineraries/${q}`, body);
  },

  createDayPlan: (itineraryId: string, body: Record<string, unknown>) =>
    apiClient.post<DayPlanDTO>(`/api/v1/itineraries/${itineraryId}/day-plans`, body),

  addActivity: (dayPlanId: string, body: Record<string, unknown>) =>
    apiClient.post<ItineraryActivityDTO>(
      `/api/v1/itineraries/day-plans/${dayPlanId}/activities`,
      body
    ),

  assignTemplate: (
    templateId: string,
    body: { guest_group_id: string; start_date: string }
  ) =>
    apiClient.post<ItineraryWithDetailsDTO>(
      `/api/v1/itineraries/templates/${templateId}/assign`,
      body
    ),

  getDayPlanMapView: (dayPlanId: string) =>
    apiClient.get<ItineraryMapViewData>(
      `/api/v1/itineraries/host/day-plans/${dayPlanId}/map-view`
    ),

  generateSuggestions: (body: {
    guest_group_id?: string | null;
    duration_days: number;
    interests?: string[];
    theme_prompt?: string | null;
    budget_level?: string;
    pace?: string;
    must_see_attractions?: string[];
    avoid_activities?: string[];
  }) =>
    apiClient.post<ItinerarySuggestionResponseDTO>(
      '/api/v1/itineraries/suggestions',
      body
    ),

  optimizeDayPlanRoute: (dayPlanId: string) =>
    apiClient.post<{ success: boolean }>(
      `/api/v1/itineraries/day-plans/${dayPlanId}/optimize-route`,
      {}
    ),

  voteActivity: (
    accessCode: string,
    activityId: string,
    vote: { vote: 'yes' | 'no' | 'maybe'; guest_name?: string; reason?: string; priority?: number }
  ) =>
    apiClient.post(
      `/api/v1/itineraries/activities/${activityId}/vote?access_code=${encodeURIComponent(accessCode)}`,
      vote
    ),

  checkInActivity: (accessCode: string, activityId: string) =>
    apiClient.post(
      `/api/v1/itineraries/activities/${activityId}/check-in?access_code=${encodeURIComponent(accessCode)}`,
      {}
    ),

  updateItinerary: (
    itineraryId: string,
    body: {
      title?: string;
      description?: string | null;
      base_location?: string;
      base_latitude?: number;
      base_longitude?: number;
    }
  ) => apiClient.put<HostItineraryRow>(`/api/v1/itineraries/${itineraryId}`, body),

  listRoutePoints: (itineraryId: string) =>
    apiClient.get<RoutePointDTO[]>(`/api/v1/itineraries/${itineraryId}/route-points`),

  createRoutePoint: (
    itineraryId: string,
    body: {
      day_plan_id: string;
      name: string;
      latitude: number;
      longitude: number;
      description?: string;
      order_index?: number;
      estimated_duration?: number;
    }
  ) =>
    apiClient.post<RoutePointDTO>(
      `/api/v1/itineraries/${itineraryId}/route-points`,
      body
    ),

  updateRoutePoint: (
    pointId: string,
    body: Partial<{
      title: string;
      description: string;
      latitude: number;
      longitude: number;
      sequence_order: number;
      estimated_duration: number;
    }>
  ) => apiClient.put<RoutePointDTO>(`/api/v1/itineraries/route-points/${pointId}`, body),

  deleteRoutePoint: (pointId: string) =>
    apiClient.delete(`/api/v1/itineraries/route-points/${pointId}`),

  reorderRoutePoints: (
    itineraryId: string,
    body: { day_plan_id: string; ordered_activity_ids: string[] }
  ) =>
    apiClient.put<{ success: boolean }>(
      `/api/v1/itineraries/${itineraryId}/route-points/reorder`,
      body
    ),
};

export interface RoutePointDTO {
  id: string;
  day_plan_id: string;
  name: string;
  latitude?: number | null;
  longitude?: number | null;
  description?: string | null;
  order_index: number;
  estimated_duration: number;
}

export const realtimeApi = {
  getUpdates: (city?: string, contentTypes?: string) => {
    const params = new URLSearchParams();
    if (city) params.append('city', city);
    if (contentTypes) params.append('content_types', contentTypes);
    const query = params.toString();
    return apiClient.get<any[]>(`/api/v1/realtime/updates${query ? `?${query}` : ''}`);
  },
  getSummary: () =>
    apiClient.get<Record<string, any>>('/api/v1/realtime/summary'),
  getSourcesStatus: () =>
    apiClient.get<any[]>('/api/v1/realtime/sources/status'),
  refresh: (sourceIds?: string) => {
    const params = sourceIds ? `?source_ids=${sourceIds}` : '';
    return apiClient.post<any>(`/api/v1/realtime/sources/refresh${params}`);
  },
};

export const onboardingApi = {
  generateProfileSuggestions: (basicInfo: any) => {
    // Map frontend data to backend API requirements - INCLUDE ALL PERSONAL DATA!
    const apiData = {
      // CRITICAL: Host personal information
      first_name: basicInfo.first_name || '',
      last_name: basicInfo.last_name || '',
      business_name: basicInfo.business_name || '',

      // Location information
      city: basicInfo.city || '',
      address: basicInfo.location || basicInfo.address || `${basicInfo.city}, ${basicInfo.region}`,
      region: basicInfo.region || 'Istria',

      // Property information
      business_type: basicInfo.property_type || basicInfo.business_type || 'apartment',
      max_group_size: basicInfo.max_group_size || 4,
      amenities: basicInfo.amenities || [],

      // Host personal details - THE MISSING CRITICAL DATA!
      local_experience: basicInfo.local_experience || '',
      location_story: basicInfo.location_story || '',
      specialties: basicInfo.specialties || [],
      preferred_guests: basicInfo.preferred_guests || [],

      // Other information
      languages: basicInfo.languages || ['hr', 'en'],
      hosting_experience: basicInfo.hosting_experience || 0,
      interests: basicInfo.specialties || basicInfo.interests || [],
      profile_style: basicInfo.profile_style || 'warm_authentic',
      target_guests: basicInfo.preferred_guests || basicInfo.target_guests || ['families', 'couples']
    };

    console.log('🚀 Sending COMPLETE host data to AI:', apiData);
    return apiClient.post('/api/v1/onboarding/generate-profile-suggestions', apiData);
  },

  generateAttractionSuggestions: (locationInfo: any, specialties: string[] = [], hostContext: any = {}) =>
    apiClient.post('/api/v1/onboarding/generate-attraction-suggestions', {
      ...locationInfo,
      specialties,
      host_context: hostContext,
    }),

  validateProfile: (profileData: any) =>
    apiClient.post('/api/v1/onboarding/validate-profile', profileData),

  enhanceAccommodation: (currentData: Record<string, unknown>, enhancementType = 'comprehensive') =>
    apiClient.post<AccommodationEnhancementResponse>('/api/v1/onboarding/accommodation/ai-enhance', {
      current_data: currentData,
      enhancement_type: enhancementType,
    }),

  sendAccommodationAgentMessage: (payload: AccommodationAgentMessageRequest) =>
    apiClient.post<AccommodationAgentMessageResponse>('/api/v1/onboarding/accommodation/agent/message', payload),

  completeOnboarding: (onboardingData: any) =>
    apiClient.post('/api/v1/onboarding/complete-onboarding', onboardingData),
};



// Location API for Google Maps integration
export const locationsApi = {
  getForGuestGroup: (guestGroupId: string, options?: {
    includeGooglePlaces?: boolean;
    includeHostAttractions?: boolean;
  }) => {
    const params = new URLSearchParams();
    if (options?.includeGooglePlaces !== undefined) {
      params.append('include_google_places', String(options.includeGooglePlaces));
    }
    if (options?.includeHostAttractions !== undefined) {
      params.append('include_host_attractions', String(options.includeHostAttractions));
    }
    const queryString = params.toString();
    return apiClient.get<{
      success: boolean;
      locations: any[];
      count: number;
      guest_group_id: string;
    }>(`/api/v1/locations/guest-group/${guestGroupId}${queryString ? `?${queryString}` : ''}`);
  },

  geocode: (params: { address: string; city?: string; county?: string }) => {
    const qs = new URLSearchParams({ address: params.address.trim() });
    if (params.city?.trim()) qs.set('city', params.city.trim());
    if (params.county?.trim()) qs.set('county', params.county.trim());
    return apiClient.get<{
      lat: number;
      lng: number;
      formatted_address: string;
      precision: string;
      matched_query: string;
    }>(`/api/v1/locations/geocode?${qs.toString()}`);
  },

  getDetails: (locationId: string, source: 'database' | 'google_places') =>
    apiClient.get<{
      success: boolean;
      location: any;
      source: string;
    }>(`/api/v1/locations/location/${locationId}?source=${source}`),

  cacheGooglePlaces: (query: string, latitude: number, longitude: number, placesData: any[]) =>
    apiClient.post('/api/v1/locations/cache/google-places', {
      query,
      latitude,
      longitude,
      places_data: placesData,
    }),

  getCacheStats: () =>
    apiClient.get<{
      success: boolean;
      cache_stats: any;
    }>('/api/v1/locations/cache/stats'),

  clearCache: () =>
    apiClient.delete<{
      success: boolean;
      message: string;
    }>('/api/v1/locations/cache/clear'),

  getNearby: (hostId: string, options?: {
    radiusKm?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    params.append('radius_km', String(options?.radiusKm ?? 10.0));
    params.append('limit', String(options?.limit ?? 20));
    return apiClient.get<{
      success: boolean;
      locations: any[];
      count: number;
      host_location: any;
      search_radius_km: number;
    }>(`/api/v1/locations/nearby/${hostId}?${params.toString()}`);
  },
};



export type CleaningProvider = {
  id: string;
  name: string;
  description?: string | null;
  partner_type: string;
  category?: string | null;
  city: string;
  region?: string | null;
  email?: string | null;
  phone?: string | null;
  website?: string | null;
  address?: string | null;
  price_range?: string | null;
  rate_card?: Record<string, unknown>;
  price_notes?: string | null;
  commission_rate?: number;
  average_rating?: number | null;
  total_reviews?: number | null;
  languages_spoken?: string[];
  ai_why?: string;
};

export const cleaningApi = {
  getProviders: (params?: { city?: string; region?: string }) => {
    const q = new URLSearchParams();
    if (params?.city) q.append("city", params.city);
    if (params?.region) q.append("region", params.region);
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return apiClient.get<{
      disclaimer_indicative_fees: string;
      providers: CleaningProvider[];
    }>(`/api/v1/cleaning/providers${suffix}`);
  },
  getMyCleaners: () =>
    apiClient.get<{ cleaners: { partner: CleaningProvider; relationship: Record<string, unknown> }[] }>(
      "/api/v1/cleaning/my-cleaners"
    ),
  linkCleaner: (partnerId: string, body?: { priority?: number; partnership_notes?: string }) =>
    apiClient.post<{ success: boolean; relationship_id: string }>("/api/v1/cleaning/my-cleaners", {
      partner_id: partnerId,
      ...body,
    }),
  unlinkCleaner: (partnerId: string) =>
    apiClient.delete<{ success: boolean }>(`/api/v1/cleaning/my-cleaners/${partnerId}`),
  getUpcomingCheckouts: () =>
    apiClient.get<{
      checkouts: {
        guest_group_id: string;
        group_name?: string | null;
        check_in_date?: string | null;
        check_out_date: string;
        group_size: number;
      }[];
    }>("/api/v1/cleaning/upcoming-checkouts"),
  getMessageContext: () =>
    apiClient.get<{
      property_name: string | null;
      address: string | null;
      city: string | null;
      county: string | null;
      next_checkout: {
        guest_group_id: string;
        group_name: string | null;
        check_out_date: string;
      } | null;
    }>("/api/v1/cleaning/message-context"),
  discover: (body?: { intent?: string; city?: string }) =>
    apiClient.post<{
      disclaimer?: string;
      ai_used?: boolean;
      fallback_reason?: string;
      ranked: CleaningProvider[];
    }>("/api/v1/cleaning/discover", body ?? {}),
  draftMessage: (body: {
    partner_id: string;
    intent?: string;
    service_date?: string;
    guest_group_id?: string;
    language?: string;
  }) =>
    apiClient.post<{ draft: string; ai_used?: boolean; fallback_reason?: string; model?: string }>(
      "/api/v1/cleaning/draft-message",
      body
    ),
  getBookings: () =>
    apiClient.get<{
      bookings: {
        id: string;
        partner_id: string | null;
        guest_group_id: string | null;
        service_date: string | null;
        status: string;
        notes: string | null;
        booking_amount: number;
        currency: string;
        booking_details: Record<string, unknown>;
        created_at: string | null;
      }[];
    }>("/api/v1/cleaning/bookings"),
  createBooking: (body: {
    partner_id: string;
    service_date?: string;
    guest_group_id?: string;
    notes?: string;
    intent?: string;
    estimated_amount?: number;
    currency?: string;
  }) => apiClient.post<{ id: string; status: string }>("/api/v1/cleaning/bookings", body),
  patchBookingStatus: (bookingId: string, status: string) =>
    apiClient.patch<{ id: string; status: string }>(`/api/v1/cleaning/bookings/${bookingId}/status`, {
      status,
    }),
  postFeedback: (bookingId: string, rating: number, comment?: string) =>
    apiClient.post<{ success: boolean }>(`/api/v1/cleaning/bookings/${bookingId}/feedback`, {
      rating,
      comment,
    }),
};

export type ChannelAccountDto = {
  id: string;
  channel: string;
  status: string;
  external_hotel_id: string | null;
  feature_enabled: boolean;
};

export const channelIntegrationsApi = {
  getStatus: () =>
    apiClient.get<{ account: ChannelAccountDto | null }>("/api/v1/channel-integrations/status"),

  connectBookingCom: (body: {
    hotel_id: string;
    api_username: string;
    api_password: string;
  }) => apiClient.post<ChannelAccountDto>("/api/v1/channel-integrations/booking-com/connect", body),

  disconnect: () =>
    apiClient.delete<{ ok: boolean; disconnected: boolean }>(
      "/api/v1/channel-integrations/booking-com/disconnect"
    ),

  syncReservations: (accountId: string) =>
    apiClient.post<Record<string, unknown>>(
      `/api/v1/channel-integrations/${accountId}/sync/reservations`
    ),

  syncFull: (accountId: string) =>
    apiClient.post<Record<string, unknown>>(`/api/v1/channel-integrations/${accountId}/sync/full`),

  getHealth: (accountId: string) =>
    apiClient.get<{
      account_id: string;
      reservations_cursor: string | null;
      last_reservations_poll_at: string | null;
      last_availability_push_at: string | null;
      last_rates_push_at: string | null;
      last_full_sync_at: string | null;
      last_error: string | null;
      consecutive_errors: number;
    }>(`/api/v1/channel-integrations/${accountId}/health`),

  createMapping: (accountId: string, body: {
    local_entity_type: "host" | "partner";
    local_entity_id: string;
    external_room_id: string;
    external_rate_id?: string;
  }) =>
    apiClient.post<{
      id: string;
      local_entity_type: string;
      local_entity_id: string;
      external_room_id: string | null;
      external_rate_id: string | null;
      active: boolean;
    }>(`/api/v1/channel-integrations/${accountId}/mappings`, body),

  pushAvailability: (
    accountId: string,
    body: { mapping_id: string; date_from: string; date_to: string; available: number }
  ) =>
    apiClient.post<{ ok: boolean }>(
      `/api/v1/channel-integrations/${accountId}/push/availability`,
      body
    ),

  pushRates: (
    accountId: string,
    body: {
      mapping_id: string;
      date_from: string;
      date_to: string;
      price: number;
      currency?: string;
    }
  ) =>
    apiClient.post<{ ok: boolean }>(`/api/v1/channel-integrations/${accountId}/push/rates`, body),

  replayEvent: (eventId: string) =>
    apiClient.post<Record<string, unknown>>(
      `/api/v1/channel-integrations/events/${eventId}/replay`
    ),
};

export type MaintenanceIssue = {
  id: string;
  host_id: string;
  guest_group_id: string | null;
  category: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  photo_urls: string[];
  due_at: string | null;
  resolved_at: string | null;
  source: string;
  source_metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export const maintenanceApi = {
  getCategories: () =>
    apiClient.get<{ categories: string[] }>("/api/v1/maintenance/categories"),
  listIssues: () =>
    apiClient.get<{ issues: MaintenanceIssue[] }>("/api/v1/maintenance/issues"),
  createIssue: (body: {
    category: string;
    title: string;
    description?: string;
    priority?: string;
    photo_urls?: string[];
  }) => apiClient.post<MaintenanceIssue>("/api/v1/maintenance/issues", body),
  suggestPartners: (issueId: string) =>
    apiClient.post<{
      ranked: Array<{
        partner_id: string;
        name: string;
        phone: string | null;
        city: string;
        distance_km: number | null;
        reason: string;
      }>;
      ai_used: boolean;
      disclaimer: string;
    }>(`/api/v1/maintenance/issues/${issueId}/suggest-partners`),
  draftMessage: (
    issueId: string,
    body: {
      partner_id: string;
      tone?: string;
      channel?: string;
      include_guest_contact?: boolean;
    }
  ) =>
    apiClient.post<{ message_hr: string; ai_used: boolean }>(
      `/api/v1/maintenance/issues/${issueId}/draft-message`,
      body
    ),
  runPreventive: () =>
    apiClient.post<{ created_count: number; issues: MaintenanceIssue[] }>(
      "/api/v1/maintenance/run-preventive"
    ),
  listSchedules: () =>
    apiClient.get<{
      schedules: Array<{
        id: string;
        title: string;
        category: string;
        interval_days: number;
        active: boolean;
        last_run_at: string | null;
        next_due_at: string | null;
      }>;
    }>("/api/v1/maintenance/schedules"),
  createSchedule: (body: {
    title: string;
    category: string;
    interval_days: number;
    next_due_at?: string | null;
  }) =>
    apiClient.post<{
      id: string;
      title: string;
      category: string;
      interval_days: number;
      next_due_at: string | null;
    }>("/api/v1/maintenance/schedules", body),
  patchIssue: (issueId: string, body: Partial<{ status: string; title: string; description: string }>) =>
    apiClient.patch<MaintenanceIssue>(`/api/v1/maintenance/issues/${issueId}`, body),
  saveDraft: (
    issueId: string,
    body: { partner_id: string; channel?: string; draft_text: string; host_edited?: boolean }
  ) =>
    apiClient.post<{ id: string; created_at: string | null }>(
      `/api/v1/maintenance/issues/${issueId}/save-draft`,
      body
    ),
  replySuggestions: (issueId: string, inbound_text: string) =>
    apiClient.post<{ suggestions: string[] }>(
      `/api/v1/maintenance/issues/${issueId}/reply-suggestions`,
      { inbound_text }
    ),
};

export type AdaptationProject = {
  id: string;
  title: string;
  brief: string | null;
  style_tags: string[];
  budget_band: string | null;
  status: string;
  assumptions_json: Record<string, unknown>;
  roi_inputs_json: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export const adaptationApi = {
  listProjects: () =>
    apiClient.get<{ projects: AdaptationProject[] }>("/api/v1/adaptation/projects"),
  createProject: (body: {
    title: string;
    brief?: string;
    style_tags?: string[];
    budget_band?: string;
  }) => apiClient.post<AdaptationProject>("/api/v1/adaptation/projects", body),
  addAsset: (projectId: string, body: { storage_url: string; kind?: string }) =>
    apiClient.post<{ id: string }>(
      `/api/v1/adaptation/projects/${projectId}/assets`,
      body
    ),
  analyze: (projectId: string) =>
    apiClient.post<Record<string, unknown>>(
      `/api/v1/adaptation/projects/${projectId}/analyze`
    ),
  getRoi: (projectId: string) =>
    apiClient.get<Record<string, unknown>>(`/api/v1/adaptation/projects/${projectId}/roi`),
  patchRoiInputs: (projectId: string, roi_inputs_json: Record<string, unknown>) =>
    apiClient.patch<AdaptationProject>(`/api/v1/adaptation/projects/${projectId}`, {
      roi_inputs_json,
    }),
  patchProject: (
    projectId: string,
    body: { documentation_notes?: string; title?: string; brief?: string }
  ) => apiClient.patch<AdaptationProject>(`/api/v1/adaptation/projects/${projectId}`, body),
  suggestSuppliers: (projectId: string, bom_category: string) =>
    apiClient.post<{
      bom_category: string;
      maintenance_category: string;
      partners: Array<{
        partner_id: string;
        name: string;
        phone: string | null;
        city: string;
        distance_km: number | null;
      }>;
      discovery?: {
        host_has_coordinates: boolean;
        any_distance_unknown: boolean;
        sort_explanation: string;
      };
    }>(`/api/v1/adaptation/projects/${projectId}/suggest-suppliers`, { bom_category }),

  assistant: (
    projectId: string,
    body: {
      message: string;
      history?: Array<{ role: "user" | "assistant"; content: string }>;
    }
  ) =>
    apiClient.post<{
      disclaimer: string;
      ai_used: boolean;
      reply: string;
      phases: Array<{
        phase_name: string;
        description: string;
        order: number;
        duration_weeks_min: number;
        duration_weeks_max: number;
        key_tasks: string[];
      }>;
      cost_orientation: string;
      timeline_overview: string;
      communication_tips: string[];
      follow_up_questions: string[];
    }>(`/api/v1/adaptation/projects/${projectId}/assistant`, body),
};

export const guestMaintenanceApi = {
  report: (body: {
    access_code: string;
    category: string;
    title: string;
    description?: string;
    photo_urls?: string[];
  }) => apiClient.post<MaintenanceIssue>("/api/v1/maintenance/guest-reports", body),
};

/** Google Maps directions / search from attraction fields */
export function mapsUrlForAttraction(a?: Attraction | null): string | null {
  if (!a) return null;
  if (typeof a.latitude === "number" && typeof a.longitude === "number") {
    return `https://www.google.com/maps/dir/?api=1&destination=${a.latitude},${a.longitude}`;
  }
  if (Array.isArray(a.coordinates) && a.coordinates.length >= 2) {
    const [x, y] = a.coordinates;
    if (typeof x === "number" && typeof y === "number") {
      return `https://www.google.com/maps/dir/?api=1&destination=${x},${y}`;
    }
  }
  const q =
    a.location?.trim() || a.city?.trim() || a.address?.trim() || a.name?.trim();
  if (q) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
  }
  return null;
}

export function openAttractionInMaps(a?: Attraction | null): void {
  const url = mapsUrlForAttraction(a);
  if (url && typeof window !== "undefined") {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

export function mapsUrlForItineraryActivity(act: ItineraryActivity): string | null {
  if (act.google_maps_url?.trim()) return act.google_maps_url.trim();
  if (typeof act.latitude === "number" && typeof act.longitude === "number") {
    return `https://www.google.com/maps/dir/?api=1&destination=${act.latitude},${act.longitude}`;
  }
  const q =
    act.address?.trim() ||
    act.location_name?.trim() ||
    act.attraction?.name?.trim();
  if (q) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
  }
  return mapsUrlForAttraction(act.attraction);
}
