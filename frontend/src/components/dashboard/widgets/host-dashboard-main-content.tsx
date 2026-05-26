"use client";

import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { GoogleMapsProvider } from "@/components/maps/GoogleMapsProvider";
import { HostMapView } from "@/components/maps/HostMapView";
import { HostLocationSearch } from "@/components/maps/HostLocationSearch";
import { ChannelIntegrationPanel } from "@/components/dashboard/channel-integration-panel";
import { InsightsTab } from "@/components/dashboard/insights-tab";
import { CleaningTab } from "@/components/dashboard/cleaning-tab";
import { OverviewTab } from "@/components/dashboard/overview-tab";
import { GuestGroupsTab } from "@/components/dashboard/guest-groups-tab";
import { AttractionsTab } from "@/components/dashboard/attractions-tab";
import { RoutesTab } from "@/components/dashboard/routes-tab";
import { MaintenanceTab } from "@/components/dashboard/maintenance-tab";
import { AdaptationTab } from "@/components/dashboard/adaptation-tab";
import { AccountTab } from "@/components/dashboard/account-tab";
import type { Attraction, GuestGroup, HostProfile } from "@/lib/api";
import type { AccommodationOverview, DashboardStatsCard } from "@/components/dashboard/dashboard-types";

type DashboardTab =
  | "overview"
  | "accommodation"
  | "channels"
  | "groups"
  | "attractions"
  | "routes"
  | "maintenance"
  | "adaptation"
  | "insights"
  | "map"
  | "discover"
  | "cleaning"
  | "account";

interface HostDashboardMainContentProps {
  activeTab: DashboardTab;
  statsCards: DashboardStatsCard[];
  guestGroups: GuestGroup[];
  realtimeUpdates: Array<{ id: string; title: string; content: string; description?: string; created_at: string }>;
  loadDashboardData: () => void;
  dashboardLoading?: boolean;
  accommodationInfo: AccommodationOverview | null;
  setProfile: React.Dispatch<React.SetStateAction<HostProfile | null>>;
  profile: HostProfile | null;
  onCreateGroup: () => void;
  onViewGroup: (group: GuestGroup) => void;
  onCopyAccessCode: (code: string) => void;
  onRegenerateAccessCode: (groupId: string) => void;
  regeneratingGroupId: string | null;
  attractions: Attraction[];
  openCreateAttractionModal: () => void;
  openEditAttractionModal: (attraction: Attraction) => void;
  openDeleteAttractionModal: (attraction: Attraction) => void;
  openViewReviewsModal: (attraction: Attraction) => void;
  openPhotoUploadModal: (attraction: Attraction) => void;
  viewMode: "list" | "map";
  onToggleViewMode: () => void;
  onPlaceSelect: (place: unknown) => void;
  onAddPlaceToAttractions: (place: unknown) => void;
  AccommodationTab: React.ComponentType<{
    accommodationInfo: AccommodationOverview | null;
    onRefresh: () => void;
    setProfile: React.Dispatch<React.SetStateAction<HostProfile | null>>;
    profile: HostProfile | null;
  }>;
}

export const HostDashboardMainContent: React.FC<HostDashboardMainContentProps> = ({
  activeTab,
  statsCards,
  guestGroups,
  realtimeUpdates,
  loadDashboardData,
  dashboardLoading,
  accommodationInfo,
  setProfile,
  profile,
  onCreateGroup,
  onViewGroup,
  onCopyAccessCode,
  onRegenerateAccessCode,
  regeneratingGroupId,
  attractions,
  openCreateAttractionModal,
  openEditAttractionModal,
  openDeleteAttractionModal,
  openViewReviewsModal,
  openPhotoUploadModal,
  viewMode,
  onToggleViewMode,
  onPlaceSelect,
  onAddPlaceToAttractions,
  AccommodationTab,
}) => {
  const renderTab = () => {
    if (activeTab === "overview") {
      return (
        <OverviewTab
          statsCards={statsCards}
          guestGroups={guestGroups}
          realtimeUpdates={realtimeUpdates}
          onRefresh={loadDashboardData}
          accommodationInfo={accommodationInfo}
          isLoading={dashboardLoading}
        />
      );
    }

    if (activeTab === "accommodation") {
      return (
        <AccommodationTab
          accommodationInfo={accommodationInfo}
          onRefresh={loadDashboardData}
          setProfile={setProfile}
          profile={profile}
        />
      );
    }

    if (activeTab === "channels") {
      return (
        <div className="max-w-4xl">
          <ChannelIntegrationPanel />
        </div>
      );
    }

    if (activeTab === "groups") {
      return (
        <GuestGroupsTab
          guestGroups={guestGroups}
          onCreateGroup={onCreateGroup}
          onViewGroup={onViewGroup}
          onCopyAccessCode={onCopyAccessCode}
          onRegenerateAccessCode={onRegenerateAccessCode}
          regeneratingGroupId={regeneratingGroupId}
        />
      );
    }

    if (activeTab === "attractions") {
      return (
        <AttractionsTab
          attractions={attractions}
          onCreateAttraction={openCreateAttractionModal}
          onEditAttraction={openEditAttractionModal}
          onDeleteAttraction={openDeleteAttractionModal}
          onViewReviews={openViewReviewsModal}
          onPhotoUpload={openPhotoUploadModal}
          viewMode={viewMode}
          onToggleViewMode={onToggleViewMode}
        />
      );
    }

    if (activeTab === "routes") {
      return (
        <RoutesTab
          guestGroups={guestGroups}
          attractions={attractions}
          onRefresh={loadDashboardData}
        />
      );
    }

    if (activeTab === "maintenance") {
      return (
        <div className="max-w-4xl">
          <MaintenanceTab />
        </div>
      );
    }

    if (activeTab === "adaptation") {
      return (
        <div className="max-w-4xl">
          <AdaptationTab />
        </div>
      );
    }

    if (activeTab === "map") {
      return (
        <GoogleMapsProvider apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ""}>
          <HostMapView
            attractions={attractions}
            onSelectAttraction={openEditAttractionModal}
            onAddNewAttraction={openCreateAttractionModal}
          />
        </GoogleMapsProvider>
      );
    }

    if (activeTab === "cleaning") {
      return <CleaningTab />;
    }

    if (activeTab === "discover") {
      return (
        <GoogleMapsProvider apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ""}>
          <HostLocationSearch onSelectPlace={onPlaceSelect} onAddToAttractions={onAddPlaceToAttractions} />
        </GoogleMapsProvider>
      );
    }

    if (activeTab === "account") {
      return <AccountTab />;
    }

    if (activeTab === "insights") {
      return (
        <InsightsTab
          realtimeUpdates={realtimeUpdates}
          onRefresh={loadDashboardData}
          hostCity={profile?.city || accommodationInfo?.property?.location?.city}
        />
      );
    }

    return null;
  };

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.section
        key={activeTab}
        initial={false}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.2 }}
        className="px-3 pb-4 sm:px-0"
      >
        {renderTab()}
      </motion.section>
    </AnimatePresence>
  );
};
