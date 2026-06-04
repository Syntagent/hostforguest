"use client";

import React from "react";
import Image from "next/image";
import { MapPin, Pencil, Plus, Save, X } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { hostsApi, type AccommodationPatch, type GuestPropertyRules, type HostProfile } from "@/lib/api";
import { isPlausibleGpsLatLng } from "@/lib/utils";
import type { AccommodationOverview } from "./dashboard-types";
import { AccommodationAiAgentPanel } from "./accommodation-ai-agent/accommodation-ai-agent-panel";
import {
  CHECKLIST_EDIT_TARGETS,
  type AccommodationSnapshot,
} from "./accommodation-ai-agent/accommodation-checklist";

type AccommodationTabProps = {
  accommodationInfo: AccommodationOverview | null;
  onRefresh: () => void;
  setProfile: React.Dispatch<React.SetStateAction<HostProfile | null>>;
  profile: HostProfile | null;
};

const defaultRules: GuestPropertyRules = {
  checkInTime: "15:00",
  checkOutTime: "11:00",
  cancellationPolicy: "Flexible cancellation up to 24 hours before arrival",
  houseRules: ["No smoking inside", "Quiet hours from 22:00 to 08:00"],
  wifiName: "",
  wifiPassword: "",
  emergencyNote: "",
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

function compactPatch(patch: AccommodationPatch): AccommodationPatch {
  return Object.fromEntries(
    Object.entries(patch).filter(([, value]) => value !== undefined && value !== null && value !== ""),
  ) as AccommodationPatch;
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
  const [editData, setEditData] = React.useState<AccommodationSnapshot>(() => toSnapshot(accommodationInfo, profile));
  const [propertyRules, setPropertyRules] = React.useState(defaultRules);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (!isEditing) setEditData(toSnapshot(accommodationInfo, profile));
  }, [accommodationInfo, isEditing, profile]);

  React.useEffect(() => {
    if (profile?.property_rules && typeof profile.property_rules === "object") {
      setPropertyRules({ ...defaultRules, ...profile.property_rules });
      return;
    }
    try {
      const raw = localStorage.getItem("tg_property_rules_v1");
      if (raw) setPropertyRules({ ...defaultRules, ...JSON.parse(raw) });
    } catch {
      /* ignore corrupt local property rules */
    }
  }, [profile?.property_rules]);

  const [geocodeStatus, setGeocodeStatus] = React.useState<
    "idle" | "loading" | "exact" | "approx" | "error"
  >("idle");
  const geocodeTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const runAddressGeocode = React.useCallback(async () => {
    const address = (editData.address || "").trim();
    const city = (editData.city || "").trim();
    const county = (editData.county || "").trim();
    if (!address && !city) {
      setGeocodeStatus("idle");
      return;
    }
    setGeocodeStatus("loading");
    const res = await hostsApi.geocodeLocation({ address: address || city, city, county });
    if (res.success && res.data) {
      setEditData((current) => ({
        ...current,
        latitude: res.data!.latitude,
        longitude: res.data!.longitude,
      }));
      setGeocodeStatus(res.data.precision === "address" ? "exact" : "approx");
    } else {
      setGeocodeStatus("error");
    }
  }, [editData.address, editData.city, editData.county]);

  React.useEffect(() => {
    if (!isEditing) return;
    if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current);
    const address = (editData.address || "").trim();
    const city = (editData.city || "").trim();
    if (!address && !city) {
      setGeocodeStatus("idle");
      return;
    }
    geocodeTimerRef.current = setTimeout(() => {
      void runAddressGeocode();
    }, 700);
    return () => {
      if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current);
    };
  }, [isEditing, editData.address, editData.city, editData.county, runAddressGeocode]);

  const snapshot = editData;

  const applyPatch = (patch: AccommodationPatch, options?: { replaceFields?: string[] }) => {
    const cleanPatch = compactPatch(patch);
    const replaceFields = new Set(options?.replaceFields || []);
    setIsEditing(true);
    setEditData((current) => ({
      ...current,
      ...cleanPatch,
      amenities: cleanPatch.amenities
        ? replaceFields.has("amenities") ? cleanPatch.amenities : mergeArrays(current.amenities, cleanPatch.amenities)
        : current.amenities,
      services_offered: cleanPatch.services_offered
        ? replaceFields.has("services_offered")
          ? cleanPatch.services_offered
          : mergeArrays(current.services_offered, cleanPatch.services_offered)
        : current.services_offered,
      expertise_areas: cleanPatch.expertise_areas
        ? replaceFields.has("expertise_areas")
          ? cleanPatch.expertise_areas
          : mergeArrays(current.expertise_areas, cleanPatch.expertise_areas)
        : current.expertise_areas,
      languages: cleanPatch.languages
        ? replaceFields.has("languages") ? cleanPatch.languages : mergeArrays(current.languages, cleanPatch.languages)
        : current.languages,
      gallery_images: cleanPatch.gallery_images
        ? replaceFields.has("gallery_images")
          ? cleanPatch.gallery_images
          : mergeArrays(current.gallery_images, cleanPatch.gallery_images)
        : current.gallery_images,
    }));
    showToast({
      type: "success",
      title: "Draft applied",
      message: "Review the fields and save when ready.",
    });
  };

  const reviewMissingFacts = () => {
    const missingFact = [
      { id: "amenities", label: "amenities", prompt: "Confirm concrete comforts like Wi-Fi, air conditioning, parking, kitchen, balcony, or washing machine." },
      { id: "services", label: "services", prompt: "Confirm services you can actually arrange, such as self check-in support, local recommendations, transfers, or cleaning." },
      { id: "gallery", label: "photos", prompt: "Add at least one real property photo." },
      { id: "welcome_message", label: "welcome message", prompt: "Write the real greeting guests should receive before arrival." },
    ].find((item) => {
      if (item.id === "amenities") return (snapshot.amenities || []).length < 3;
      if (item.id === "services") return (snapshot.services_offered || []).length < 1;
      if (item.id === "gallery") return (snapshot.gallery_images || []).length < 1;
      if (item.id === "welcome_message") return !(snapshot.welcome_message || "").trim();
      return false;
    });

    if (missingFact) {
      focusMissingField(missingFact.id);
      showToast({
        type: "success",
        title: `Review ${missingFact.label}`,
        message: missingFact.prompt,
      });
      return;
    }

    showToast({
      type: "success",
      title: "Facts look complete",
      message: "Use the assistant chat or voice button to refine wording from real host details.",
    });
  };

  const save = async () => {
    setIsSaving(true);
    const response = await hostsApi.updateProfile({
      ...editData,
      property_rules: propertyRules,
    });
    if (response.success && response.data) {
      setProfile((current) => ({ ...(current || response.data!), ...response.data! }));
      localStorage.setItem("tg_property_rules_v1", JSON.stringify(propertyRules));
      setIsEditing(false);
      onRefresh();
      showToast({ type: "success", title: "Accommodation saved", message: "Your accommodation profile is updated." });
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

  const removeListItem = (
    field: "amenities" | "services_offered" | "expertise_areas" | "languages",
    valueToRemove: string
  ) => {
    setEditData((current) => ({
      ...current,
      [field]: (current[field] || []).filter((value) => value !== valueToRemove),
    }));
    setIsEditing(true);
  };

  const focusMissingField = (checklistId: string) => {
    setIsEditing(true);
    window.requestAnimationFrame(() => {
      const targetId = CHECKLIST_EDIT_TARGETS[checklistId];
      if (!targetId) return;
      const target = document.getElementById(targetId);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
      const firstInput = target?.querySelector<HTMLElement>("input, textarea, select, button");
      firstInput?.focus({ preventScroll: true });
    });
  };

  const gpsReady = isPlausibleGpsLatLng(snapshot.latitude, snapshot.longitude);

  return (
    <div className="space-y-3 sm:space-y-5">
      <div className="rounded-2xl border border-border/70 bg-card/80 p-3 shadow-sm sm:rounded-3xl sm:p-5">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-primary/70 sm:text-[11px] sm:tracking-[0.18em]">Accommodation</p>
            <h2 className="truncate text-base font-semibold text-foreground sm:mt-1 sm:text-xl">Property profile</h2>
            <p className="hidden text-sm text-muted-foreground sm:block">
              Guided AI onboarding turns your strongest host knowledge into guest-ready facts.
            </p>
          </div>
          <div className="flex shrink-0 gap-1.5 sm:gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditing(true)}
              className="h-8 w-8 min-h-0 rounded-xl p-0 sm:h-auto sm:w-auto sm:min-h-10 sm:px-4"
              aria-label="Edit accommodation profile"
              title="Edit"
            >
              <Pencil className="h-4 w-4" />
              <span className="hidden sm:ml-1 sm:inline">Edit</span>
            </Button>
            <Button
              size="sm"
              onClick={save}
              disabled={!isEditing || isSaving}
              className="h-8 w-8 min-h-0 rounded-xl p-0 sm:h-auto sm:w-auto sm:min-h-10 sm:px-4"
              aria-label="Save accommodation profile changes"
              title={isSaving ? "Saving" : "Save"}
            >
              <Save className="h-4 w-4" />
              <span className="hidden sm:ml-1 sm:inline">{isSaving ? "Saving..." : "Save Changes"}</span>
            </Button>
          </div>
        </div>
      </div>

      <AccommodationAiAgentPanel
        snapshot={snapshot}
        voiceEnabled
        onApplyPatch={applyPatch}
        onEnhanceAll={reviewMissingFacts}
        onEditMissing={focusMissingField}
      />

      <div className="grid grid-cols-1 gap-3 sm:gap-4 lg:grid-cols-3">
          <Card id="stay-property-details" className="scroll-mt-20">
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
            <div id="stay-capacity" className="grid scroll-mt-20 grid-cols-2 gap-3">
              <Field label="Guests">
                <input type="number" min={1} value={snapshot.max_guests || ""} onChange={(e) => {
                  setEditData((current) => ({
                    ...current,
                    max_guests: e.target.value ? Number(e.target.value) : undefined,
                  }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
              <Field label="Rooms">
                <input type="number" min={1} value={snapshot.number_of_rooms || ""} onChange={(e) => {
                  setEditData((current) => ({
                    ...current,
                    number_of_rooms: e.target.value ? Number(e.target.value) : undefined,
                  }));
                  setIsEditing(true);
                }} className="w-full rounded-md border px-3 py-2" />
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card id="stay-location" className="scroll-mt-20">
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
              {geocodeStatus === "loading"
                ? "Verifying address on map…"
                : geocodeStatus === "exact"
                  ? "Location verified from your address."
                  : geocodeStatus === "approx"
                    ? "Approximate location — add street + city for best accuracy."
                    : geocodeStatus === "error"
                      ? "Could not verify address — check city/county or set GPS manually."
                      : gpsReady
                        ? "GPS is ready for distance recommendations."
                        : "GPS is still needed for accurate guest suggestions."}
            </p>
          </CardContent>
        </Card>

        <Card id="stay-guest-voice" className="scroll-mt-20">
          <CardHeader>
            <CardTitle>Guest Voice</CardTitle>
            <CardDescription>Description and welcome message</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Field label="Property story">
              <textarea value={snapshot.location_story || ""} rows={3} onChange={(e) => {
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

      <div className="grid grid-cols-1 gap-3 sm:gap-4 lg:grid-cols-2">
          <Card id="stay-amenities" className="scroll-mt-20">
          <CardHeader>
            <CardTitle>Amenities, Services, Specialties</CardTitle>
            <CardDescription>Checkable facts the agent can promote</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 sm:space-y-4">
            <ChipEditor
              label="Amenities"
              values={snapshot.amenities || []}
              onAdd={(value) => updateList("amenities", value)}
              onRemove={(value) => removeListItem("amenities", value)}
            />
            <ChipEditor
              label="Services"
              values={snapshot.services_offered || []}
              onAdd={(value) => updateList("services_offered", value)}
              onRemove={(value) => removeListItem("services_offered", value)}
            />
            <ChipEditor
              label="Specialties"
              values={snapshot.expertise_areas || []}
              onAdd={(value) => updateList("expertise_areas", value)}
              onRemove={(value) => removeListItem("expertise_areas", value)}
            />
            <ChipEditor
              label="Languages"
              values={snapshot.languages || []}
              onAdd={(value) => updateList("languages", value)}
              onRemove={(value) => removeListItem("languages", value)}
            />
          </CardContent>
        </Card>

        <Card id="stay-photos-rules" className="scroll-mt-20">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Photos And Rules</CardTitle>
              <CardDescription>Visual trust and house basics</CardDescription>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              className="h-8 min-h-0 rounded-xl px-3 text-xs sm:h-auto sm:min-h-10 sm:rounded-2xl sm:text-sm"
            >
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">Add Photos</span>
              <span className="sm:hidden">Add</span>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3 sm:space-y-4">
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
                <div className="flex h-20 min-w-44 items-center justify-center rounded-2xl border border-dashed text-sm text-gray-500 sm:h-28 sm:min-w-56">
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
              <textarea value={propertyRules.cancellationPolicy} rows={2} onChange={(e) => {
                setPropertyRules((current) => ({ ...current, cancellationPolicy: e.target.value }));
                setIsEditing(true);
              }} className="w-full rounded-md border px-3 py-2" />
            </Field>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="WiFi network">
                <input
                  value={propertyRules.wifiName || ""}
                  onChange={(e) => {
                    setPropertyRules((current) => ({ ...current, wifiName: e.target.value }));
                    setIsEditing(true);
                  }}
                  className="w-full rounded-md border px-3 py-2"
                  placeholder="Network name"
                />
              </Field>
              <Field label="WiFi password">
                <input
                  value={propertyRules.wifiPassword || ""}
                  onChange={(e) => {
                    setPropertyRules((current) => ({ ...current, wifiPassword: e.target.value }));
                    setIsEditing(true);
                  }}
                  className="w-full rounded-md border px-3 py-2"
                  placeholder="Password"
                />
              </Field>
            </div>
            <Field label="Emergency note for guests">
              <textarea
                value={propertyRules.emergencyNote || ""}
                rows={2}
                onChange={(e) => {
                  setPropertyRules((current) => ({ ...current, emergencyNote: e.target.value }));
                  setIsEditing(true);
                }}
                className="w-full rounded-md border px-3 py-2"
                placeholder="e.g. Building manager: +385… · Nearest clinic: …"
              />
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

function ChipEditor({
  label,
  values,
  onAdd,
  onRemove,
}: {
  label: string;
  values: string[];
  onAdd: (value: string) => void;
  onRemove: (value: string) => void;
}) {
  const [draft, setDraft] = React.useState("");
  const hasValues = values.length > 0;
  return (
    <div className="rounded-2xl bg-muted/30 p-2 sm:bg-transparent sm:p-0">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-800">{label}</p>
        {!hasValues && <span className="text-xs font-medium text-amber-700">Missing</span>}
      </div>
      {hasValues && (
        <div className="mb-2 flex gap-2 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible sm:pb-0">
          {values.map((value) => (
            <span
              key={value}
              className="inline-flex shrink-0 items-center gap-1 rounded-full bg-blue-50 py-1 pl-3 pr-1 text-xs font-medium text-blue-800"
            >
              <span>{value.replace(/_/g, " ")}</span>
              <button
                type="button"
                onClick={() => onRemove(value)}
                className="rounded-full p-0.5 text-blue-700 transition hover:bg-blue-100 hover:text-blue-950 focus:outline-none focus:ring-2 focus:ring-blue-400"
                aria-label={`Remove ${value.replace(/_/g, " ")} from ${label}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-1.5 sm:gap-2">
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
          className="min-w-0 flex-1 rounded-xl border px-3 py-2 text-sm"
        />
        <Button type="button" variant="outline" size="sm" onClick={() => {
          onAdd(draft);
          setDraft("");
        }} className="h-9 min-h-0 rounded-xl px-3 text-xs sm:h-auto sm:min-h-10 sm:rounded-2xl sm:text-sm">
          Add
        </Button>
      </div>
    </div>
  );
}

