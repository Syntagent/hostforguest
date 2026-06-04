export type GuestLocale = "en" | "hr";

const STORAGE_PREFIX = "tg_guest_locale_";

export function resolveGuestLocale(
  preferredLanguage?: string | null,
  accessCode?: string
): GuestLocale {
  if (typeof window !== "undefined" && accessCode) {
    const stored = localStorage.getItem(`${STORAGE_PREFIX}${accessCode}`);
    if (stored === "hr" || stored === "en") return stored;
  }
  const lang = (preferredLanguage || "").trim().toLowerCase();
  if (lang.startsWith("hr") || lang === "croatian") return "hr";
  return "en";
}

export function persistGuestLocale(accessCode: string, locale: GuestLocale) {
  if (typeof window === "undefined") return;
  localStorage.setItem(`${STORAGE_PREFIX}${accessCode}`, locale);
}

type GuestCopyKey =
  | "eventsForStay"
  | "timingDuringStay"
  | "timingNearStay"
  | "shortTrip"
  | "easyHalfDay"
  | "planHalfDay"
  | "worthDayTrip"
  | "furtherAfield"
  | "savedEvents"
  | "hostPlanned"
  | "inItinerary"
  | "planTabTitle"
  | "assistantEventsSuggestion";

const COPY: Record<GuestLocale, Record<GuestCopyKey, string>> = {
  en: {
    eventsForStay: "Events for your stay",
    timingDuringStay: "During your stay",
    timingNearStay: "Near your stay",
    shortTrip: "Short trip from your stay",
    easyHalfDay: "Easy half-day outing",
    planHalfDay: "Plan a half-day trip",
    worthDayTrip: "Worth a day trip",
    furtherAfield: "Further afield — check travel time",
    savedEvents: "Saved event ideas",
    hostPlanned: "Host planned",
    inItinerary: "In itinerary",
    planTabTitle: "Plan",
    assistantEventsSuggestion: "What's on the events list this week?",
  },
  hr: {
    eventsForStay: "Događaji za vaš boravak",
    timingDuringStay: "Tijekom boravka",
    timingNearStay: "Blizu boravka",
    shortTrip: "Kratak izlet od smještaja",
    easyHalfDay: "Lagani poludnevni izlet",
    planHalfDay: "Planirajte poludnevni izlet",
    worthDayTrip: "Vrijedi cjelodnevnog izleta",
    furtherAfield: "Dalje — provjerite vrijeme putovanja",
    savedEvents: "Spremljene ideje za događaje",
    hostPlanned: "Domaćin planirao",
    inItinerary: "U itinereru",
    planTabTitle: "Plan",
    assistantEventsSuggestion: "Što je na popisu događaja ovaj tjedan?",
  },
};

export function guestCopy(locale: GuestLocale, key: GuestCopyKey): string {
  return COPY[locale][key] ?? COPY.en[key];
}
