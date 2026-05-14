"use client";

import React from "react";
import type {
  Attraction,
  GuestEVisitorData,
  GuestEVisitorDataCreate,
  GuestGroup,
  HostProfile,
} from "@/lib/api";
import { GoogleMapsProvider } from "@/components/maps/GoogleMapsProvider";
import {
  EnhancedAttractionModal,
  type EnhancedPlace,
} from "@/components/maps/EnhancedAttractionModal";
import { AttractionAnalyticsModal } from "@/components/dashboard/AttractionAnalyticsModal";
import { PhotoUploadModal } from "@/components/dashboard/PhotoUploadModal";
import { CreateGroupModal, GroupDetailsModal } from "@/components/dashboard/group-modals";
import { DeleteAttractionModal } from "@/components/dashboard/delete-attraction-modal";
import { EVisitorDataModal, CreateEVisitorModal } from "@/components/dashboard/evisitor-modal";
import type { CreateGroupFormData } from "@/components/dashboard/dashboard-types";

interface HostDashboardModalsProps {
  showCreateGroupModal: boolean;
  setShowCreateGroupModal: (open: boolean) => void;
  showGroupDetailsModal: boolean;
  setShowGroupDetailsModal: (open: boolean) => void;
  selectedGroup: GuestGroup | null;
  copyAccessCode: (code: string) => void;
  onRegenerateAccessCode: (groupId: string) => void;
  regeneratingGroupId: string | null;
  loadEVisitorData: (groupId: string) => void;
  setShowEVisitorModal: (open: boolean) => void;
  handleCreateGroup: () => Promise<void> | void;
  createGroupData: CreateGroupFormData;
  setCreateGroupData: React.Dispatch<React.SetStateAction<CreateGroupFormData>>;
  showCreateAttractionModal: boolean;
  setShowCreateAttractionModal: (open: boolean) => void;
  handleCreateAttraction: () => Promise<void> | void;
  createAttractionData: Record<string, unknown>;
  setCreateAttractionData: React.Dispatch<React.SetStateAction<Record<string, unknown>>>;
  selectedPlace: unknown;
  showEditAttractionModal: boolean;
  selectedAttraction: Attraction | null;
  setShowEditAttractionModal: (open: boolean) => void;
  handleEditAttraction: () => Promise<void> | void;
  showDeleteAttractionModal: boolean;
  setShowDeleteAttractionModal: (open: boolean) => void;
  handleDeleteAttraction: () => Promise<void> | void;
  showAnalyticsModal: boolean;
  setShowAnalyticsModal: (open: boolean) => void;
  showPhotoUploadModal: boolean;
  setShowPhotoUploadModal: (open: boolean) => void;
  handlePhotoUpload: (attractionId: string, photos: File[]) => Promise<void>;
  showEVisitorModal: boolean;
  evisitorData: GuestEVisitorData[];
  setShowCreateEVisitorModal: (open: boolean) => void;
  setSelectedEVisitor: (record: GuestEVisitorData | null) => void;
  setCreateEVisitorData: React.Dispatch<React.SetStateAction<GuestEVisitorDataCreate>>;
  handleDeleteEVisitor: (id: string) => Promise<void> | void;
  handleMarkEVisitorRegistered: (id: string, confirmationNumber: string) => Promise<void> | void;
  showCreateEVisitorModal: boolean;
  showEditEVisitorModal: boolean;
  setShowEditEVisitorModal: (open: boolean) => void;
  handleUpdateEVisitor: () => Promise<void> | void;
  handleCreateEVisitor: () => Promise<void> | void;
  createEVisitorData: GuestEVisitorDataCreate;
  /** Saved host profile for “linked property” copy in Create Group. */
  hostProfileForGuestGroups: HostProfile | null;
}

export const HostDashboardModals: React.FC<HostDashboardModalsProps> = ({
  showCreateGroupModal,
  setShowCreateGroupModal,
  showGroupDetailsModal,
  setShowGroupDetailsModal,
  selectedGroup,
  copyAccessCode,
  onRegenerateAccessCode,
  regeneratingGroupId,
  loadEVisitorData,
  setShowEVisitorModal,
  handleCreateGroup,
  createGroupData,
  setCreateGroupData,
  showCreateAttractionModal,
  setShowCreateAttractionModal,
  handleCreateAttraction,
  createAttractionData,
  setCreateAttractionData,
  selectedPlace,
  showEditAttractionModal,
  selectedAttraction,
  setShowEditAttractionModal,
  handleEditAttraction,
  showDeleteAttractionModal,
  setShowDeleteAttractionModal,
  handleDeleteAttraction,
  showAnalyticsModal,
  setShowAnalyticsModal,
  showPhotoUploadModal,
  setShowPhotoUploadModal,
  handlePhotoUpload,
  showEVisitorModal,
  evisitorData,
  setShowCreateEVisitorModal,
  setSelectedEVisitor,
  setCreateEVisitorData,
  handleDeleteEVisitor,
  handleMarkEVisitorRegistered,
  showCreateEVisitorModal,
  showEditEVisitorModal,
  setShowEditEVisitorModal,
  handleUpdateEVisitor,
  handleCreateEVisitor,
  createEVisitorData,
  hostProfileForGuestGroups,
}) => {
  const accommodationPreview =
    hostProfileForGuestGroups &&
    (hostProfileForGuestGroups.property_name?.trim() ||
      hostProfileForGuestGroups.city?.trim() ||
      hostProfileForGuestGroups.address?.trim())
      ? {
          propertyName: hostProfileForGuestGroups.property_name?.trim() || undefined,
          city: hostProfileForGuestGroups.city?.trim() || undefined,
          address: hostProfileForGuestGroups.address?.trim() || undefined,
        }
      : null;

  return (
    <>
      {showCreateGroupModal && (
        <CreateGroupModal
          isOpen={showCreateGroupModal}
          onClose={() => setShowCreateGroupModal(false)}
          onSubmit={handleCreateGroup}
          data={createGroupData}
          onChange={setCreateGroupData}
          accommodationPreview={accommodationPreview}
        />
      )}

      {showGroupDetailsModal && selectedGroup && (
        <GroupDetailsModal
          isOpen={showGroupDetailsModal}
          onClose={() => setShowGroupDetailsModal(false)}
          group={selectedGroup}
          onCopyAccessCode={copyAccessCode}
          onRegenerateAccessCode={onRegenerateAccessCode}
          regeneratingGroupId={regeneratingGroupId}
          onManageEVisitorData={(groupId) => {
            loadEVisitorData(groupId);
            setShowEVisitorModal(true);
          }}
        />
      )}

      {showCreateAttractionModal && (
        <GoogleMapsProvider apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ""}>
          <EnhancedAttractionModal
            isOpen={showCreateAttractionModal}
            onClose={() => setShowCreateAttractionModal(false)}
            onSubmit={handleCreateAttraction}
            data={createAttractionData}
            onChange={setCreateAttractionData}
            mode="create"
            selectedPlace={(selectedPlace as EnhancedPlace | null) ?? null}
          />
        </GoogleMapsProvider>
      )}

      {showEditAttractionModal && selectedAttraction && (
        <GoogleMapsProvider apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ""}>
          <EnhancedAttractionModal
            isOpen={showEditAttractionModal}
            onClose={() => setShowEditAttractionModal(false)}
            onSubmit={handleEditAttraction}
            data={createAttractionData}
            onChange={setCreateAttractionData}
            mode="edit"
            selectedPlace={(selectedPlace as EnhancedPlace | null) ?? null}
          />
        </GoogleMapsProvider>
      )}

      {showDeleteAttractionModal && selectedAttraction && (
        <DeleteAttractionModal
          isOpen={showDeleteAttractionModal}
          onClose={() => setShowDeleteAttractionModal(false)}
          onConfirm={handleDeleteAttraction}
          attraction={selectedAttraction}
        />
      )}

      <AttractionAnalyticsModal
        isOpen={showAnalyticsModal}
        onClose={() => setShowAnalyticsModal(false)}
        attraction={selectedAttraction}
      />

      <PhotoUploadModal
        isOpen={showPhotoUploadModal}
        onClose={() => setShowPhotoUploadModal(false)}
        attraction={selectedAttraction}
        onPhotoUpload={handlePhotoUpload}
      />

      <EVisitorDataModal
        isOpen={showEVisitorModal}
        onClose={() => setShowEVisitorModal(false)}
        evisitorData={evisitorData}
        onCreateNew={() => setShowCreateEVisitorModal(true)}
        onEdit={(evisitor) => {
          setSelectedEVisitor(evisitor);
          setCreateEVisitorData({
            first_name: evisitor.first_name,
            last_name: evisitor.last_name,
            date_of_birth: evisitor.date_of_birth,
            nationality: evisitor.nationality,
            id_type: evisitor.id_type,
            id_number: evisitor.id_number,
            id_issuing_country: evisitor.id_issuing_country,
            id_expiry_date: evisitor.id_expiry_date || "",
            address_line1: evisitor.address_line1 || "",
            address_line2: evisitor.address_line2 || "",
            city: evisitor.city || "",
            state_province: evisitor.state_province || "",
            postal_code: evisitor.postal_code || "",
            country: evisitor.country || "",
            arrival_date: evisitor.arrival_date,
            departure_date: evisitor.departure_date,
            email: evisitor.email || "",
            phone: evisitor.phone || "",
          });
          setShowEditEVisitorModal(true);
        }}
        onDelete={handleDeleteEVisitor}
        onMarkRegistered={handleMarkEVisitorRegistered}
      />

      <CreateEVisitorModal
        isOpen={showCreateEVisitorModal || showEditEVisitorModal}
        onClose={() => {
          setShowCreateEVisitorModal(false);
          setShowEditEVisitorModal(false);
          setSelectedEVisitor(null);
          setCreateEVisitorData({
            first_name: "",
            last_name: "",
            date_of_birth: "",
            nationality: "",
            id_type: "passport",
            id_number: "",
            id_issuing_country: "",
            arrival_date: "",
            departure_date: "",
            email: "",
            phone: "",
          });
        }}
        onSubmit={showEditEVisitorModal ? handleUpdateEVisitor : handleCreateEVisitor}
        data={createEVisitorData}
        onChange={setCreateEVisitorData}
        mode={showEditEVisitorModal ? "edit" : "create"}
      />
    </>
  );
};
