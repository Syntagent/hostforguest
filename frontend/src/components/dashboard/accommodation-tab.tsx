"use client";

import React from "react";
import Image from "next/image";
import { MapPin, Pencil, Plus, Save, X } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { hostsApi, onboardingApi, type AccommodationPatch, type HostProfile } from "@/lib/api";
import { isPlausibleGpsLatLng } from "@/lib/utils";
import type { AccommodationOverview } from "./dashboard-types";
import { AccommodationAiAgentPanel } from "./accommodation-ai-agent/accommodation-ai-agent-panel";
import type { AccommodationSnapshot } from "./accommodation-ai-agent/accommodation-checklist";

type AccommodationTabProps = {
  accommodationInfo: AccommodationOverview | null;
  onRefresh: () => void;
  setProfile: React.Dispatch<React.SetStateAction<HostProfile | null>>;
  profile: HostProfile | null;
};

const defaultRules = {
  checkInTime: "15:00",
  checkOutTime: "11:00",
  cancellationPolicy: "Flexible cancellation up to 24 hours before arrival",
  houseRules: ["No smoking inside", "Quiet hours from 22:00 to 08:00"],
};

function toSnapshot(accommodationInfo: AccommodationOverview | null, profile: HostProfile | null): AccommodationSnapshot {
  const coordinates = accommodationInfo?.property?.location?.coordinates;
  return {
    property_name: accommodationInfo?.property?.name || profile?.property_name || "",
    property_type: accommodationInfo?.property?.type || profile?.property_type || "",
    max_guests: accommodationInfo?.property?.capacity?.maxGuests || profile?.max_guests || 0,
    number_of_rooms: accommodationInfo?.property?.capacity?.rooms || profile?.number_of_rooms || 0,
    city: accommodationInfo?.property?.location?.city || profile?.city || "",
    county: accommodationInfo?.property?.location?.county || profile?.county || "",
    address: accommodationInfo?.property?.location?.address || profile?.address || "",
    latitude: coordinates?.lat ?? profile?.latitude,
    longitude: coordinates?.lng ?? profile?.longitude,
    location_story: accommodationInfo?.description || profile?.location_story || "",
    amenities: accommodationInfo?.services?.amenities || profile?.amenities || [],
    services_offered: accommodationInfo?.services?.servicesOffered || profile?.services_offered || [],
    expertise_areas: accommodationInfo?.services?.specialties || profile?.expertise_areas || [],
    languages: accommodationInfo?.services?.languages || profile?.languages || ["hr", "en"],
    welcome_message: accommodationInfo?.welcomeMessage || profile?.welcome_message || "",
    gallery_images: profile?.gallery_images || [],
    propertyRulesComplete: true,
  };
}

function mergeArrays(existing: string[] | undefined, incoming: string[] | undefined) {
  return [...new Set([...(existing || []), ...(incoming || [])].filter(Boolean))];
}

export const AccommodationTab: React.FC<AccommodationTabProps> = ({
  accommodationInfo,
  onRefresh,
  setProfile,
  profile,
}) => {
  const { showToast } = useToast();
  const [isEditing, setIsEditing] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isEnhancingAll, setIsEnhancingAll] = React.useState(false);
  const [editData, setEditData] = React.useState<AccommodationSnapshot>(() => toSnapshot(accommodationInfo, profile));
  const [propertyRules, setPropertyRules] = React.useState(defaultRules);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (!isEditing) setEditData(toSnapshot(accommodationInfo, profile));
  }, [accommodationInfo, isEditing, profile]);

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem("tg_property_rules_v1");
      if (raw) setPropertyRules({ ...defaultRules, ...JSON.parse(raw) });
    } catch {
      /* ignore corrupt local property rules */
    }
  }, []);

  const snapshot = editData;

  const applyPatch = (patch: AccommodationPatch) => {
    setIsEditing(true);
    setEditData((current) => ({
      ...current,
      ...patch,
      amenities: patch.amenities ? mergeArrays(current.amenities, patch.amenities) : current.amenities,
      services_offered: patch.services_offered
        ? mergeArrays(current.services_offered, patch.services_offered)
        : current.services_offered,
      expertise_areas: patch.expertise_areas
        ? mergeArrays(current.expertise_areas, patch.expertise_areas)
        : current.expertise_areas,
      languages: patch.languages ? mergeArrays(current.languages, patch.languages) : current.languages,
      gallery_images: patch.gallery_images ? mergeArrays(current.gallery_images, patch.gallery_images) : current.gallery_images,
    }));
    showToast({
      type: "success",
      title: "Draft applied",
      message: "Review the fields and save when ready.",
    });
  };

  const enhanceAll = async () => {
    setIsEnhancingAll(true);
    const response = await onboardingApi.enhanceAccommodation(snapshot as Record<string, unknown>);
    if (response.success && response.data?.enhanced_content) {
      const enhanced = response.data.enhanced_content;
      applyPatch({
        location_story: enhanced.description,
        amenities: enhanced.amenities,
        services_offered: enhanced.services,
        expertise_areas: enhanced.specialties,
        languages: enhanced.languages,
        welcome_message: enhanced.welcome_message,
      });
    } else {
      showToast({
        type: "error",
        title: "AI enhancement failed",
        message: response.error || "Try again after checking your AI settings.",
      });
    }
    setIsEnhancingAll(false);
  };

  const save = async () => {
    setIsSaving(true);
    const response = await hostsApi.updateProfile(editData);
    if (response.success && response.data) {
      setProfile((current) => ({ ...(current || response.data!), ...response.data! }));
      localStorage.setItem("tg_property_rules_v1", JSON.stringify(propertyRules));
      setIsEditing(false);
      onRefresh();
      showToast({ type: "success", title: "Accommodation saved", message: "Your Stay profile is updated." });
    } else {
      showToast({ type: "error", title: "Save failed", message: response.error || "Could not save the profile." });
    }
    setIsSaving(false);
  };

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setEditData((current) => ({
          ...current,
          gallery_images: [...(current.gallery_images || []), reader.result as string],
        }));
        setIsEditing(true);
      };
      reader.readAsDataURL(file);
    });
  };

  const updateList = (field: "amenities" | "services_offered" | "expertise_areas" | "languages", value: string) => {
    if (!value.trim()) return;
    setEditData((current) => ({ ...current, [field]: mergeArrays(current[field], [value.trim()]) }));
    setIsEditing(true);
  };

  const gpsReady = isPlausibleGpsLatLng(snapshot.latitude, snapshot.longitude);

  return (
    <div className="space-y-5">
      <div className="rounded-3xl border border-border/70 bg-card/80 p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary/70">Stay</p>
            <h2 className="mt-1 text-lg font-semibold text-foreground sm:text-xl">Property profile</h2>
            <p className="text-sm text-muted-foreground">
              Guided AI onboarding turns your strongest host knowledge into guest-ready facts.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
              <Pencil className="h-4 w-4" />
              Edit
            </Button>
            <Button size="sm" onClick={save} disabled={!isEditing || isSaving}>
              <Save className="h-4 w-4" />
              {isSaving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </div>

      <AccommodationAiAgentPanel
        snapshot={snapshot}
        voiceEnabled
        onApplyPatch={applyPatch}
        onEnhanceAll={enhanceAll}
        isEnhancingAll={isEnhancingAll}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Property Details</CardTitle>
            <CardDescription>Name, type, and capacity</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Field label="Property name">
              <input value={snapshot.property_name || ""} onChange={(e) => {
                setEditData((current) => ({ ...current, property_name: e.target.value }));
                setIsEditing(true);
              }} className="w-full rounded-md border px-3 py-2" />
            </Field>
            <Field label="Property type">
              <select value={snapshot.property_type || ""} onChange={(e) => {
                setEditData((current) => ({ ...current, property_type: e.target.value }));
                setIsEditing(true);
              }} className="w-full rounded-md border px-3 py-2">
                <option value="">Select type</option>
                <option value="apartment">Apartment</option>
                <option value="house">House</option>
                <option value="villa">Villa</option>
                <option value="room">Private room</option>
                <option value="cabin">Cabin</option>
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Guests">
                <input type="number" min={1} value={snapshot.max_guests || ""} onChange={(e) => {
                  setEditData((current) => ({ ...current, max_guests: Number(e.target.value) || 1 }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
              <Field label="Rooms">
                <input type="number" min={1} value={snapshot.number_of_rooms || ""} onChange={(e) => {
                  setEditData((current) => ({ ...current, number_of_rooms: Number(e.target.value) || 1 }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Location</CardTitle>
            <CardDescription>Trust and map accuracy</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(["city", "county", "address"] as const).map((field) => (
              <Field key={field} label={field.replace("_", " ")}>
                <input value={snapshot[field] || ""} onChange={(e) => {
                  setEditData((current) => ({ ...current, [field]: e.target.value }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
            ))}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Latitude">
                <input type="number" step="0.0001" value={snapshot.latitude ?? ""} onChange={(e) => {
                  const value = e.target.value ? Number(e.target.value) : undefined;
                  setEditData((current) => ({ ...current, latitude: value }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
              <Field label="Longitude">
                <input type="number" step="0.0001" value={snapshot.longitude ?? ""} onChange={(e) => {
                  const value = e.target.value ? Number(e.target.value) : undefined;
                  setEditData((current) => ({ ...current, longitude: value }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
            </div>
            <p className={gpsReady ? "text-xs text-green-700" : "text-xs text-amber-700"}>
              <MapPin className="mr-1 inline h-3 w-3" />
              {gpsReady ? "GPS is ready for distance recommendations." : "GPS is still needed for accurate guest suggestions."}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Guest Voice</CardTitle>
            <CardDescription>Description and welcome message</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Field label="Property story">
              <textarea value={snapshot.location_story || ""} rows={5} onChange={(e) => {
                setEditData((current) => ({ ...current, location_story: e.target.value }));
                setIsEditing(true);
              }} className="w-full rounded-md border px-3 py-2" />
            </Field>
            <Field label="Welcome message">
              <input value={snapshot.welcome_message || ""} onChange={(e) => {
                setEditData((current) => ({ ...current, welcome_message: e.target.value }));
                setIsEditing(true);
              }} className="w-full rounded-md border px-3 py-2" />
            </Field>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Amenities, Services, Specialties</CardTitle>
            <CardDescription>Checkable facts the agent can promote</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ChipEditor label="Amenities" values={snapshot.amenities || []} onAdd={(value) => updateList("amenities", value)} />
            <ChipEditor label="Services" values={snapshot.services_offered || []} onAdd={(value) => updateList("services_offered", value)} />
            <ChipEditor label="Specialties" values={snapshot.expertise_areas || []} onAdd={(value) => updateList("expertise_areas", value)} />
            <ChipEditor label="Languages" values={snapshot.languages || []} onAdd={(value) => updateList("languages", value)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Photos And Rules</CardTitle>
              <CardDescription>Visual trust and house basics</CardDescription>
            </div>
            <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()}>
              <Plus className="h-4 w-4" />
              Add Photos
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleImageUpload} />
            <div className="flex gap-3 overflow-x-auto pb-2">
              {(snapshot.gallery_images || []).map((src, index) => (
                <div key={`${src}-${index}`} className="relative h-28 w-28 shrink-0 overflow-hidden rounded-2xl bg-gray-100">
                  <Image src={src} alt={`Property photo ${index + 1}`} fill className="object-cover" unoptimized />
                  <button type="button" className="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white" onClick={() => {
                    setEditData((current) => ({
                      ...current,
                      gallery_images: (current.gallery_images || []).filter((_, i) => i !== index),
                    }));
                    setIsEditing(true);
                  }}>
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
              {(snapshot.gallery_images || []).length === 0 && (
                <div className="flex h-28 min-w-56 items-center justify-center rounded-2xl border border-dashed text-sm text-gray-500">
                  No photos yet
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Check-in">
                <input type="time" value={propertyRules.checkInTime} onChange={(e) => {
                  setPropertyRules((current) => ({ ...current, checkInTime: e.target.value }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
              <Field label="Check-out">
                <input type="time" value={propertyRules.checkOutTime} onChange={(e) => {
                  setPropertyRules((current) => ({ ...current, checkOutTime: e.target.value }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
            </div>
            <Field label="Cancellation policy">
              <textarea value={propertyRules.cancellationPolicy} rows={3} onChange={(e) => {
                setPropertyRules((current) => ({ ...current, cancellationPolicy: e.target.value }));
                setIsEditing(true);
              }} className="w-full rounded-md border px-3 py-2" />
            </Field>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold capitalize text-gray-600">{label}</span>
      {children}
    </label>
  );
}

function ChipEditor({ label, values, onAdd }: { label: string; values: string[]; onAdd: (value: string) => void }) {
  const [draft, setDraft] = React.useState("");
  return (
    <div>
      <p className="mb-2 text-sm font-semibold text-gray-800">{label}</p>
      <div className="mb-2 flex flex-wrap gap-2">
        {values.length > 0 ? values.map((value) => (
          <span key={value} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800">
            {value.replace(/_/g, " ")}
          </span>
        )) : <span className="text-sm text-gray-500">None yet</span>}
      </div>
      <div className="flex gap-2">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onAdd(draft);
              setDraft("");
            }
          }}
          placeholder={`Add ${label.toLowerCase()}`}
          className="flex-1 rounded-md border px-3 py-2 text-sm"
        />
        <Button type="button" variant="outline" size="sm" onClick={() => {
          onAdd(draft);
          setDraft("");
        }}>
          Add
        </Button>
      </div>
    </div>
  );
}

