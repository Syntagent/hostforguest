import type { ReactNode } from "react";

export interface DashboardAnalytics {
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
}

export interface CreateGroupFormData {
  group_name: string;
  group_size: number;
  preferences: Array<{
    guest_name: string;
    age_range: string;
    interests: string[];
    mobility_level: string;
    budget_level: string;
    language_preference: string;
  }>;
}

/** Nested shape used by overview / accommodation UI (API may omit fields). */
export interface AccommodationOverview {
  property?: {
    name?: string;
    type?: string;
    location?: {
      address?: string;
      city?: string;
      county?: string;
      coordinates?: { lat: number; lng: number };
    };
    capacity?: { maxGuests?: number; rooms?: number };
  };
  services?: {
    amenities?: string[];
    servicesOffered?: string[];
    languages?: string[];
    specialties?: string[];
  };
  description?: string;
  welcomeMessage?: string;
}

export interface DashboardStatsCard {
  title: string;
  value: string | number;
  description: string;
  icon: ReactNode;
  trend: string;
  trendUp: boolean;
}

export interface RealtimeUpdateSnippet {
  id: string;
  title: string;
  content: string;
  created_at: string;
  description?: string;
}
