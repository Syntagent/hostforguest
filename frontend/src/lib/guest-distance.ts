/**
 * Guest-facing distance labels (straight-line km from stay to event).
 * Road distance is typically ~1.2–1.5× in coastal Kvarner.
 */

import { type GuestLocale, guestCopy } from "@/lib/guest-i18n";

export function formatGuestDistanceKm(km: number | null | undefined): string | null {
  if (km == null || !Number.isFinite(km)) return null;
  const rounded = km < 10 ? Math.round(km * 10) / 10 : Math.round(km);
  return `~${rounded} km`;
}

export function guestDistanceHint(
  km: number | null | undefined,
  locale: GuestLocale = "en"
): string | null {
  if (km == null || !Number.isFinite(km)) return null;
  if (km <= 3) return guestCopy(locale, "shortTrip");
  if (km <= 8) return guestCopy(locale, "easyHalfDay");
  if (km <= 20) return guestCopy(locale, "planHalfDay");
  if (km <= 40) return guestCopy(locale, "worthDayTrip");
  return guestCopy(locale, "furtherAfield");
}

export function formatGuestDistanceLabel(
  km: number | null | undefined,
  locale: GuestLocale = "en"
): string | null {
  const dist = formatGuestDistanceKm(km);
  if (!dist) return null;
  const hint = guestDistanceHint(km, locale);
  return hint ? `${dist} · ${hint}` : dist;
}
