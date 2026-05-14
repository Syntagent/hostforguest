"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { guestGroupsApi, type GuestGroup } from "@/lib/api";
import type { CreateGroupFormData } from "./dashboard-types";

export const CreateGroupModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSubmit: () => void;
  data: CreateGroupFormData;
  onChange: (data: CreateGroupFormData) => void;
  /** Current saved accommodation (host profile) — new groups link to this property. */
  accommodationPreview?: {
    propertyName?: string;
    city?: string;
    address?: string;
  } | null;
}> = ({ isOpen, onClose, onSubmit, data, onChange, accommodationPreview }) => {
  useEffect(() => {
    const preferencesLength = data?.preferences?.length || 0;
    if (isOpen && preferencesLength === 0) {
      onChange({
        ...data,
        preferences: [
          {
            guest_name: "",
            age_range: "adult",
            interests: [],
            mobility_level: "high",
            budget_level: "medium",
            language_preference: "en",
          },
        ],
      });
    }
  }, [isOpen, data?.preferences?.length, onChange, data]);

  useEffect(() => {
    const preferencesLength = data?.preferences?.length || 0;
    if (data.group_size !== preferencesLength) {
      onChange({
        ...data,
        group_size: preferencesLength,
      });
    }
  }, [data?.preferences?.length, onChange, data]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Create New Guest Group</h2>
          <Button variant="ghost" onClick={onClose}>
            ✕
          </Button>
        </div>

        <div className="space-y-6">
          {accommodationPreview &&
          (accommodationPreview.propertyName ||
            accommodationPreview.city ||
            accommodationPreview.address) ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50/90 p-4">
              <h3 className="text-sm font-semibold text-emerald-900">Linked property</h3>
              <p className="mt-1 text-xs text-emerald-800/90">
                This guest group will be tied to the accommodation below (same as your Accommodation tab).
                Update the property there anytime; group cards show the current details.
              </p>
              <ul className="mt-2 space-y-0.5 text-sm text-emerald-950">
                {accommodationPreview.propertyName ? (
                  <li>
                    <span className="font-medium">Name:</span> {accommodationPreview.propertyName}
                  </li>
                ) : null}
                {accommodationPreview.city ? (
                  <li>
                    <span className="font-medium">City:</span> {accommodationPreview.city}
                  </li>
                ) : null}
                {accommodationPreview.address ? (
                  <li>
                    <span className="font-medium">Address:</span> {accommodationPreview.address}
                  </li>
                ) : null}
              </ul>
            </div>
          ) : (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <strong>No accommodation profile yet.</strong> Save your property under{" "}
              <span className="font-medium">Accommodation</span> so new guest groups link to it (name,
              address, GPS).
            </div>
          )}

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Group Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={data.group_name}
              onChange={(e) => onChange({ ...data, group_name: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Smith Family, Business Trip Group"
              required
            />
            {!data.group_name && (
              <p className="mt-1 text-sm text-red-500">
                Group name is required to create a group
              </p>
            )}
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Group Size</label>
            <input
              type="number"
              min={1}
              max={20}
              value={data.group_size}
              onChange={(e) =>
                onChange({ ...data, group_size: parseInt(e.target.value, 10) || 1 })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-sm text-gray-500">Number of guests in this group</p>
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <h3 className="mb-2 text-lg font-medium text-blue-900">
              📋 Guest Information Collection
            </h3>
            <p className="mb-3 text-sm text-blue-800">After creating this group, guests will be able to:</p>
            <ul className="mb-3 space-y-1 text-sm text-blue-800">
              <li>• Access the group using the provided access code</li>
              <li>• Fill in their personal preferences and interests</li>
              <li>• Provide e-visitor registration data for Croatia</li>
              <li>• Receive personalized recommendations</li>
            </ul>
            <p className="text-sm text-blue-700">
              <strong>Note:</strong> You don&apos;t need to fill in guest preferences now — guests
              will provide this information when they join the group.
            </p>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            gradient
            onClick={onSubmit}
            disabled={!data.group_name}
            title={!data.group_name ? "Please enter a group name" : "Create the guest group"}
          >
            Create Group
          </Button>
        </div>
      </div>
    </div>
  );
};

export const GroupDetailsModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  group: GuestGroup;
  onCopyAccessCode: (accessCode: string) => void;
  onRegenerateAccessCode: (groupId: string) => void;
  regeneratingGroupId: string | null;
  onManageEVisitorData: (groupId: string) => void;
}> = ({
  isOpen,
  onClose,
  group,
  onCopyAccessCode,
  onRegenerateAccessCode,
  regeneratingGroupId,
  onManageEVisitorData,
}) => {
  const [openingGuest, setOpeningGuest] = useState(false);

  const openGuestView = async () => {
    setOpeningGuest(true);
    try {
      const res = await guestGroupsApi.getHostGuestExperience(group.id);
      if (!res.success || !res.data) {
        window.alert(res.error || "Could not load guest link.");
        return;
      }
      if (!res.data.guest_app_path) {
        window.alert(
          "No active access code for this group (or it expired). Create or regenerate a code, then try again."
        );
        return;
      }
      const url = `${window.location.origin}${res.data.guest_app_path}`;
      window.open(url, "_blank", "noopener,noreferrer");
    } finally {
      setOpeningGuest(false);
    }
  };

  if (!isOpen) return null;

  const preferences = group.preferences || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">{group.group_name}</h2>
          <Button variant="ghost" onClick={onClose}>
            ✕
          </Button>
        </div>

        <div className="space-y-6">
          {group.accommodation &&
          (group.accommodation.property_name ||
            group.accommodation.city ||
            group.accommodation.address) ? (
            <Card className="border-emerald-200 bg-emerald-50/50">
              <CardHeader>
                <CardTitle className="text-emerald-900">Property (accommodation)</CardTitle>
                <CardDescription>Linked host profile for this group</CardDescription>
              </CardHeader>
              <CardContent className="space-y-1 text-sm text-gray-800">
                {group.accommodation.property_name ? (
                  <p>
                    <span className="font-medium text-gray-700">Name:</span>{" "}
                    {group.accommodation.property_name}
                  </p>
                ) : null}
                {group.accommodation.property_type ? (
                  <p>
                    <span className="font-medium text-gray-700">Type:</span>{" "}
                    {group.accommodation.property_type}
                  </p>
                ) : null}
                {group.accommodation.address ? (
                  <p>
                    <span className="font-medium text-gray-700">Address:</span>{" "}
                    {group.accommodation.address}
                  </p>
                ) : null}
                {group.accommodation.city ? (
                  <p>
                    <span className="font-medium text-gray-700">City:</span> {group.accommodation.city}
                  </p>
                ) : null}
                {group.accommodation.county ? (
                  <p>
                    <span className="font-medium text-gray-700">County:</span>{" "}
                    {group.accommodation.county}
                  </p>
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Group Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Status</label>
                  <span
                    className={cn(
                      "mt-1 inline-block rounded-full px-2 py-1 text-xs font-medium",
                      group.status === "active" && "bg-green-100 text-green-700",
                      group.status === "pending" && "bg-yellow-100 text-yellow-700",
                      group.status === "completed" && "bg-gray-100 text-gray-700"
                    )}
                  >
                    {group.status}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Group Size</label>
                  <p className="text-gray-900">{group.group_size} guests</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Created</label>
                  <p className="text-gray-900">
                    {new Date(group.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Access Code</label>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <code className="rounded bg-gray-100 px-2 py-1 font-mono text-sm">
                      {group.access_code ?? "— (load via Open guest view or API)"}
                    </code>
                    {group.access_code ? (
                      <>
                        <Button size="sm" variant="outline" onClick={() => onCopyAccessCode(group.access_code!)}>
                          Copy
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={String(regeneratingGroupId) === String(group.id)}
                          onClick={() => onRegenerateAccessCode(String(group.id))}
                        >
                          {String(regeneratingGroupId) === String(group.id) ? "Regenerating…" : "New code"}
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={String(regeneratingGroupId) === String(group.id)}
                        onClick={() => onRegenerateAccessCode(String(group.id))}
                      >
                        {String(regeneratingGroupId) === String(group.id) ? "Generating…" : "Generate code"}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={openingGuest}
                      onClick={() => void openGuestView()}
                    >
                      {openingGuest ? "Opening…" : "Open guest view"}
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Guest Preferences</CardTitle>
              <CardDescription>
                Guest preferences will appear here once guests join and provide their information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {preferences.length > 0 ? (
                  preferences.map((pref, index) => (
                    <div key={index} className="rounded-lg border border-gray-200 p-4">
                      <h4 className="mb-2 font-medium">
                        {pref.guest_name || `Guest ${index + 1}`}
                      </h4>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Age Range:</span>
                          <span className="ml-2 capitalize">{pref.age_range}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Mobility:</span>
                          <span className="ml-2 capitalize">{pref.mobility_level}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Budget:</span>
                          <span className="ml-2 capitalize">{pref.budget_level}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Language:</span>
                          <span className="ml-2 capitalize">{pref.language_preference}</span>
                        </div>
                        {pref.interests && pref.interests.length > 0 && (
                          <div className="col-span-2">
                            <span className="text-gray-600">Interests:</span>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {pref.interests.map((interest, i) => (
                                <span
                                  key={i}
                                  className="rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-700"
                                >
                                  {interest}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-lg border border-gray-200 p-4 text-center">
                    <div className="mb-2 text-gray-400">👥</div>
                    <p className="mb-2 text-gray-500">No guest preferences available yet</p>
                    <p className="text-sm text-gray-400">
                      Guests need to join using the access code and provide their preferences
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>🇭🇷 E-Visitor Registration Data</CardTitle>
              <CardDescription>
                Manage Croatian e-visitor registration data for guests
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="rounded-lg border border-gray-200 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h4 className="font-medium text-gray-900">E-Visitor Data Management</h4>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onManageEVisitorData(group.id)}
                    >
                      📝 Manage E-Visitor Data
                    </Button>
                  </div>
                  <p className="mb-3 text-sm text-gray-600">
                    Add and manage e-visitor registration data for Croatian tourism requirements.
                  </p>
                  <div className="text-sm text-gray-500">
                    <p>• Required fields: Name, Date of Birth, Nationality, ID/Passport details</p>
                    <p>• Address of residence and stay dates</p>
                    <p>• Registration status and confirmation numbers</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-6 flex gap-3">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button gradient type="button" disabled title="Coming soon">
            Send Message to Group
          </Button>
        </div>
      </div>
    </div>
  );
};
