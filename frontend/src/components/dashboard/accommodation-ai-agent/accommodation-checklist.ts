import { isPlausibleGpsLatLng } from "@/lib/utils";
import type {
  AccommodationChecklistItemState,
  AccommodationChecklistStatus,
  AccommodationPatch,
} from "@/lib/api";

export type AccommodationSnapshot = AccommodationPatch & {
  propertyRulesComplete?: boolean;
};

export type AccommodationChecklistDefinition = {
  id: string;
  label: string;
  prompt: string;
};

export const ACCOMMODATION_CHECKLIST: AccommodationChecklistDefinition[] = [
  { id: "property_name", label: "Property name", prompt: "What name should guests remember?" },
  { id: "property_type", label: "Property type", prompt: "Is it an apartment, villa, house, room, or cabin?" },
  { id: "capacity", label: "Guest capacity", prompt: "How many guests and rooms can you host comfortably?" },
  { id: "location_core", label: "City and address", prompt: "Where exactly is the property?" },
  { id: "gps", label: "Map coordinates", prompt: "Can we confirm the map pin for distance-based suggestions?" },
  { id: "location_story", label: "Property story", prompt: "What makes the stay special for guests?" },
  { id: "amenities", label: "Amenities", prompt: "Which practical comforts should guests know about?" },
  { id: "services", label: "Services", prompt: "What extra help can you arrange?" },
  { id: "specialties", label: "Local specialties", prompt: "What local topics do guests ask you about?" },
  { id: "languages", label: "Languages", prompt: "Which languages can you use with guests?" },
  { id: "welcome_message", label: "Welcome message", prompt: "How do you greet guests before arrival?" },
  { id: "gallery", label: "Photos", prompt: "Add at least one clear property photo." },
  { id: "rules", label: "House rules", prompt: "Confirm check-in/out, quiet hours, pets, and cancellation basics." },
];

const PLACEHOLDERS = new Set(["", "not set", "city not set", "address not set", "county not set"]);

function realText(value: unknown, minLength = 1): boolean {
  if (typeof value !== "string") return false;
  const normalized = value.trim().toLowerCase();
  return normalized.length >= minLength && !PLACEHOLDERS.has(normalized);
}

function hasArray(value: unknown, min = 1): boolean {
  return Array.isArray(value) && value.filter(Boolean).length >= min;
}

function itemIsDone(id: string, snapshot: AccommodationSnapshot): boolean {
  switch (id) {
    case "property_name":
      return realText(snapshot.property_name);
    case "property_type":
      return realText(snapshot.property_type);
    case "capacity":
      return Number(snapshot.max_guests || 0) >= 1 && Number(snapshot.number_of_rooms || 0) >= 1;
    case "location_core":
      return realText(snapshot.city) && realText(snapshot.address);
    case "gps":
      return isPlausibleGpsLatLng(snapshot.latitude, snapshot.longitude);
    case "location_story":
      return realText(snapshot.location_story, 80);
    case "amenities":
      return hasArray(snapshot.amenities, 3);
    case "services":
      return hasArray(snapshot.services_offered, 1);
    case "specialties":
      return hasArray(snapshot.expertise_areas, 1);
    case "languages":
      return hasArray(snapshot.languages, 1);
    case "welcome_message":
      return realText(snapshot.welcome_message, 10);
    case "gallery":
      return hasArray(snapshot.gallery_images, 1);
    case "rules":
      return Boolean(snapshot.propertyRulesComplete);
    default:
      return false;
  }
}

export function buildAccommodationChecklist(
  snapshot: AccommodationSnapshot,
  existing: AccommodationChecklistItemState[] = []
): AccommodationChecklistItemState[] {
  const existingById = new Map(existing.map((item) => [item.id, item]));
  return ACCOMMODATION_CHECKLIST.map((definition) => {
    const previous = existingById.get(definition.id);
    const status: AccommodationChecklistStatus = itemIsDone(definition.id, snapshot)
      ? "done"
      : previous?.status === "draft" || previous?.status === "skipped"
        ? previous.status
        : "missing";
    return {
      id: definition.id,
      label: definition.label,
      status,
      notes: previous?.notes,
    };
  });
}

export function getNextChecklistItem(checklist: AccommodationChecklistItemState[]) {
  return checklist.find((item) => item.status === "missing" || item.status === "in_progress") ?? checklist[0];
}

export function checklistProgress(checklist: AccommodationChecklistItemState[]): number {
  if (!checklist.length) return 0;
  const complete = checklist.filter((item) => item.status === "done" || item.status === "draft").length;
  return Math.round((complete / checklist.length) * 100);
}

