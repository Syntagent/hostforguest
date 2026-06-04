"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { guestGroupsApi, type GuestEVisitorData, type GuestGroup, type GuestPreferenceRecord } from "@/lib/api";
import type { CreateGroupFormData } from "./dashboard-types";
import {
  dateInputToCheckInIso,
  dateInputToCheckOutIso,
  formatStayDate,
  formatStayNightCount,
  getStayPhase,
  groupPropertyLabel,
  isoToDateInput,
  stayPhaseLabel,
  validateStayDates,
} from "./guest-group-stay";

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
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4">
      <div className="max-h-[min(90vh,calc(100dvh-5rem))] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:rounded-lg sm:p-6">
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

          <div className="rounded-lg border border-indigo-200 bg-indigo-50/80 p-4">
            <h3 className="text-sm font-semibold text-indigo-950">Stay schedule</h3>
            <p className="mt-1 text-xs text-indigo-900/90">
              When guests arrive and leave your property. Groups are sorted on the dashboard like a
              calendar (soonest arrival first). Guests see these dates in their guide.
            </p>
            {accommodationPreview &&
            (accommodationPreview.propertyName ||
              accommodationPreview.city ||
              accommodationPreview.address) ? (
              <p className="mt-2 text-xs font-medium text-indigo-950">
                Location:{" "}
                {[
                  accommodationPreview.propertyName,
                  accommodationPreview.city,
                  accommodationPreview.address,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            ) : null}
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Arrival (check-in) <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={data.check_in_date}
                  onChange={(e) => onChange({ ...data, check_in_date: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Departure (check-out) <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={data.check_out_date}
                  min={data.check_in_date || undefined}
                  onChange={(e) => onChange({ ...data, check_out_date: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>
            {validateStayDates(data.check_in_date, data.check_out_date) ? (
              <p className="mt-2 text-sm text-red-600">
                {validateStayDates(data.check_in_date, data.check_out_date)}
              </p>
            ) : data.check_in_date && data.check_out_date ? (
              <p className="mt-2 text-sm text-indigo-800">
                {(() => {
                  const n = formatStayNightCount(
                    dateInputToCheckInIso(data.check_in_date),
                    dateInputToCheckOutIso(data.check_out_date)
                  );
                  return n != null ? `${n} night${n === 1 ? "" : "s"} at your property` : null;
                })()}
              </p>
            ) : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Group Size</label>
            <input
              type="number"
              min={1}
              max={20}
              value={data.group_size}
              onChange={(e) => {
                const parsed = Number.parseInt(e.target.value, 10);
                if (!Number.isFinite(parsed)) return;
                onChange({
                  ...data,
                  group_size: Math.min(20, Math.max(1, parsed)),
                });
              }}
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
            disabled={
              !data.group_name ||
              !!validateStayDates(data.check_in_date, data.check_out_date)
            }
            title={
              !data.group_name
                ? "Please enter a group name"
                : validateStayDates(data.check_in_date, data.check_out_date) ||
                  "Create the guest group"
            }
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
  onGroupUpdated?: (group: GuestGroup) => void;
  onDeleteGroup?: (group: GuestGroup) => void;
  deletingGroupId?: string | null;
}> = ({
  isOpen,
  onClose,
  group,
  onCopyAccessCode,
  onRegenerateAccessCode,
  regeneratingGroupId,
  onManageEVisitorData,
  onGroupUpdated,
  onDeleteGroup,
  deletingGroupId,
}) => {
  const [openingGuest, setOpeningGuest] = useState(false);
  const [editingStay, setEditingStay] = useState(false);
  const [stayCheckIn, setStayCheckIn] = useState("");
  const [stayCheckOut, setStayCheckOut] = useState("");
  const [savingStay, setSavingStay] = useState(false);
  const [staySaveError, setStaySaveError] = useState<string | null>(null);
  const [loadedPreferences, setLoadedPreferences] = useState<GuestPreferenceRecord[]>([]);
  const [loadedEvisitor, setLoadedEvisitor] = useState<GuestEVisitorData[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setEditingStay(false);
    setStayCheckIn(isoToDateInput(group.check_in_date));
    setStayCheckOut(isoToDateInput(group.check_out_date));
    setStaySaveError(null);
  }, [isOpen, group.id, group.check_in_date, group.check_out_date]);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setLoadingDetails(true);
    setLoadedPreferences([]);
    setLoadedEvisitor([]);
    (async () => {
      try {
        const code = group.access_code;
        const tasks: Promise<void>[] = [
          guestGroupsApi.getEVisitorData(group.id).then((res) => {
            if (!cancelled && res.success && Array.isArray(res.data)) {
              setLoadedEvisitor(res.data);
            }
          }),
        ];
        if (code) {
          tasks.push(
            guestGroupsApi.getGuestPreferences(code).then((res) => {
              if (!cancelled && res.success && Array.isArray(res.data)) {
                setLoadedPreferences(res.data);
              }
            })
          );
        }
        await Promise.all(tasks);
      } finally {
        if (!cancelled) setLoadingDetails(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isOpen, group.id, group.access_code]);

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

  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const preferences =
    loadedPreferences.length > 0 ? loadedPreferences : group.preferences || [];
  const tagList = (items?: string[] | null) =>
    items && items.length > 0 ? (
      <div className="mt-1 flex flex-wrap gap-1">
        {items.map((item) => (
          <span key={item} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
            {item}
          </span>
        ))}
      </div>
    ) : (
      <span className="text-gray-500">—</span>
    );

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4">
      <div className="max-h-[min(90vh,calc(100dvh-5rem))] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:rounded-lg sm:p-6">
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

          <Card className="border-indigo-200 bg-indigo-50/40">
            <CardHeader>
              <CardTitle className="text-indigo-950">Stay at your property</CardTitle>
              <CardDescription>
                {groupPropertyLabel(group)
                  ? `Location: ${groupPropertyLabel(group)}`
                  : "Link accommodation to show the property address"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "rounded-full px-2 py-1 text-xs font-medium",
                    getStayPhase(group) === "in_house" && "bg-green-100 text-green-800",
                    getStayPhase(group) === "upcoming" && "bg-blue-100 text-blue-800",
                    getStayPhase(group) === "completed" && "bg-gray-100 text-gray-700",
                    getStayPhase(group) === "unknown" && "bg-amber-100 text-amber-900"
                  )}
                >
                  {stayPhaseLabel(getStayPhase(group))}
                </span>
              </div>
              {editingStay ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Arrival (check-in)
                      </label>
                      <input
                        type="date"
                        value={stayCheckIn}
                        onChange={(e) => setStayCheckIn(e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Departure (check-out)
                      </label>
                      <input
                        type="date"
                        value={stayCheckOut}
                        min={stayCheckIn || undefined}
                        onChange={(e) => setStayCheckOut(e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                      />
                    </div>
                  </div>
                  {staySaveError ? (
                    <p className="text-sm text-red-600">{staySaveError}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      gradient
                      disabled={savingStay}
                      onClick={async () => {
                        const err = validateStayDates(stayCheckIn, stayCheckOut);
                        if (err) {
                          setStaySaveError(err);
                          return;
                        }
                        setSavingStay(true);
                        setStaySaveError(null);
                        try {
                          const res = await guestGroupsApi.update(group.id, {
                            check_in_date: dateInputToCheckInIso(stayCheckIn),
                            check_out_date: dateInputToCheckOutIso(stayCheckOut),
                          });
                          if (!res.success || !res.data) {
                            setStaySaveError(res.error || "Could not save stay dates.");
                            return;
                          }
                          onGroupUpdated?.(res.data);
                          setEditingStay(false);
                        } finally {
                          setSavingStay(false);
                        }
                      }}
                    >
                      {savingStay ? "Saving…" : "Save dates"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={savingStay}
                      onClick={() => {
                        setEditingStay(false);
                        setStayCheckIn(isoToDateInput(group.check_in_date));
                        setStayCheckOut(isoToDateInput(group.check_out_date));
                        setStaySaveError(null);
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                  <div className="rounded-lg border border-indigo-100 bg-white p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                      Arrives
                    </p>
                    <p className="mt-1 font-semibold text-gray-900">
                      {formatStayDate(group.check_in_date)}
                    </p>
                  </div>
                  <div className="rounded-lg border border-indigo-100 bg-white p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                      Leaves
                    </p>
                    <p className="mt-1 font-semibold text-gray-900">
                      {formatStayDate(group.check_out_date)}
                    </p>
                  </div>
                  {group.check_in_date && group.check_out_date ? (
                    <p className="text-gray-600 sm:col-span-2">
                      {formatStayNightCount(group.check_in_date, group.check_out_date) ?? "—"}{" "}
                      night
                      {formatStayNightCount(group.check_in_date, group.check_out_date) === 1
                        ? ""
                        : "s"}
                    </p>
                  ) : (
                    <p className="text-amber-800 sm:col-span-2">
                      Add arrival and departure so event recommendations and guest timelines match
                      the stay.
                    </p>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    className="sm:col-span-2 sm:w-auto"
                    onClick={() => setEditingStay(true)}
                  >
                    Edit stay dates
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {(group.saved_event_recommendations?.length ?? 0) > 0 ? (
            <Card className="border-violet-200 bg-violet-50/50">
              <CardHeader>
                <CardTitle className="text-violet-950">Guest saved events</CardTitle>
                <CardDescription>
                  Events your guests saved from their guide — mark as planned when you are arranging
                  tickets or transport.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {(group.saved_event_recommendations || []).map((ev) => (
                  <div
                    key={ev.event_id}
                    className="rounded-lg border border-violet-100 bg-white p-3 text-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="font-semibold text-gray-900">{ev.title || ev.event_id}</p>
                      {ev.host_status === "planned" ? (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
                          Planned
                        </span>
                      ) : ev.guest_action === "plan_request" ? (
                        <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800">
                          Guest asked to plan
                        </span>
                      ) : null}
                    </div>
                    {ev.plan_hint ? (
                      <p className="mt-1 text-xs text-gray-600">{ev.plan_hint}</p>
                    ) : null}
                    {ev.host_status !== "planned" ? (
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-2"
                        onClick={async () => {
                          const res = await guestGroupsApi.updateSavedEventForHost(group.id, ev.event_id, {
                            host_status: "planned",
                            host_note: "Marked planned from host dashboard",
                          });
                          if (res.success && res.data?.saved_events) {
                            onGroupUpdated?.({
                              ...group,
                              saved_event_recommendations: res.data.saved_events,
                            });
                          }
                        }}
                      >
                        Mark planned
                      </Button>
                    ) : null}
                  </div>
                ))}
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
                {loadingDetails ? (
                  <p className="text-sm text-gray-500">Loading guest profiles…</p>
                ) : null}
                {preferences.length > 0 ? (
                  preferences.map((pref, index) => {
                    const rec = pref as GuestPreferenceRecord;
                    const interests = rec.personal_interests || pref.interests || [];
                    return (
                      <div key={rec.id || index} className="rounded-lg border border-gray-200 p-4">
                        <h4 className="mb-2 font-medium">
                          {pref.guest_name || `Guest ${index + 1}`}
                        </h4>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-gray-600">Age:</span>
                            <span className="ml-2 capitalize">
                              {rec.age_category || pref.age_range || "—"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">Language:</span>
                            <span className="ml-2 capitalize">{pref.language_preference}</span>
                          </div>
                          {interests.length > 0 ? (
                            <div className="col-span-2">
                              <span className="text-gray-600">Interests:</span>
                              {tagList(interests)}
                            </div>
                          ) : null}
                          {rec.dietary_needs && rec.dietary_needs.length > 0 ? (
                            <div className="col-span-2">
                              <span className="text-gray-600">Dietary:</span>
                              {tagList(rec.dietary_needs)}
                            </div>
                          ) : null}
                          {rec.mobility_notes ? (
                            <div className="col-span-2 whitespace-pre-line text-gray-700">
                              {rec.mobility_notes}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    );
                  })
                ) : !loadingDetails ? (
                  <div className="rounded-lg border border-gray-200 p-4 text-center">
                    <div className="mb-2 text-gray-400">👥</div>
                    <p className="mb-2 text-gray-500">No guest preferences available yet</p>
                    <p className="text-sm text-gray-400">
                      Guests need to join using the access code and provide their preferences
                    </p>
                  </div>
                ) : null}
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
                  {loadedEvisitor.length > 0 ? (
                    <ul className="mb-3 space-y-1 text-sm text-gray-800">
                      {loadedEvisitor.map((ev) => (
                        <li key={ev.id}>
                          {ev.first_name} {ev.last_name} · {ev.nationality}
                          {ev.evisitor_registered ? " · registered" : " · pending"}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mb-3 text-sm text-amber-800">No e-visitor records loaded.</p>
                  )}
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

        <div className="mt-6 flex flex-wrap gap-3">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          {onDeleteGroup ? (
            <Button
              variant="outline"
              className="border-red-200 text-red-700 hover:bg-red-50"
              disabled={String(deletingGroupId) === String(group.id)}
              onClick={() => onDeleteGroup(group)}
            >
              {String(deletingGroupId) === String(group.id) ? "Deleting…" : "Delete group"}
            </Button>
          ) : null}
          <Button gradient type="button" disabled title="Coming soon">
            Send Message to Group
          </Button>
        </div>
      </div>
    </div>
  );
};
