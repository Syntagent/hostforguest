import type { GuestGroup } from "@/lib/api";

/** Default stay: tomorrow check-in, +7 nights (common short stay). */
export function defaultStayDateStrings(): { check_in_date: string; check_out_date: string } {
  const inD = new Date();
  inD.setDate(inD.getDate() + 1);
  const outD = new Date(inD);
  outD.setDate(outD.getDate() + 7);
  return {
    check_in_date: toDateInputValue(inD),
    check_out_date: toDateInputValue(outD),
  };
}

export function toDateInputValue(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Map date input (YYYY-MM-DD) to API datetime (check-in 15:00, check-out 10:00 local). */
export function dateInputToCheckInIso(dateStr: string): string {
  return `${dateStr}T15:00:00`;
}

export function dateInputToCheckOutIso(dateStr: string): string {
  return `${dateStr}T10:00:00`;
}

export function isoToDateInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return toDateInputValue(d);
}

export function formatStayDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatStayNightCount(checkIn: string, checkOut: string): number | null {
  const inD = new Date(checkIn);
  const outD = new Date(checkOut);
  if (Number.isNaN(inD.getTime()) || Number.isNaN(outD.getTime())) return null;
  const start = new Date(inD.getFullYear(), inD.getMonth(), inD.getDate());
  const end = new Date(outD.getFullYear(), outD.getMonth(), outD.getDate());
  const nights = Math.round((end.getTime() - start.getTime()) / 86400000);
  return nights > 0 ? nights : null;
}

export type StayPhase = "upcoming" | "in_house" | "completed" | "unknown";

export function getStayPhase(group: GuestGroup): StayPhase {
  const inStr = group.check_in_date;
  const outStr = group.check_out_date;
  if (!inStr || !outStr) return "unknown";
  const inD = new Date(inStr);
  const outD = new Date(outStr);
  if (Number.isNaN(inD.getTime()) || Number.isNaN(outD.getTime())) return "unknown";
  const today = new Date();
  const start = new Date(inD.getFullYear(), inD.getMonth(), inD.getDate());
  const end = new Date(outD.getFullYear(), outD.getMonth(), outD.getDate());
  const now = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  if (now < start) return "upcoming";
  if (now > end) return "completed";
  return "in_house";
}

export function stayPhaseLabel(phase: StayPhase): string {
  switch (phase) {
    case "upcoming":
      return "Arriving soon";
    case "in_house":
      return "Currently staying";
    case "completed":
      return "Stay ended";
    default:
      return "Dates not set";
  }
}

export function groupPropertyLabel(group: GuestGroup): string | null {
  const acc = group.accommodation;
  if (!acc) return null;
  return (
    acc.property_name?.trim() ||
    [acc.city, acc.address?.split(",")[0]?.trim()].filter(Boolean).join(" · ") ||
    null
  );
}

/** Calendar order: soonest check-in first; undated groups last (newest created first). */
export function sortGuestGroupsByStay(groups: GuestGroup[]): GuestGroup[] {
  const withDates: GuestGroup[] = [];
  const withoutDates: GuestGroup[] = [];
  for (const g of groups) {
    if (g.check_in_date && g.check_out_date) withDates.push(g);
    else withoutDates.push(g);
  }
  withDates.sort((a, b) => {
    const ta = new Date(a.check_in_date!).getTime();
    const tb = new Date(b.check_in_date!).getTime();
    if (ta !== tb) return ta - tb;
    return new Date(a.check_out_date!).getTime() - new Date(b.check_out_date!).getTime();
  });
  withoutDates.sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
  return [...withDates, ...withoutDates];
}

export function validateStayDates(
  checkIn: string,
  checkOut: string
): string | null {
  if (!checkIn?.trim() || !checkOut?.trim()) {
    return "Arrival and departure dates are required.";
  }
  const inD = new Date(dateInputToCheckInIso(checkIn));
  const outD = new Date(dateInputToCheckOutIso(checkOut));
  if (Number.isNaN(inD.getTime()) || Number.isNaN(outD.getTime())) {
    return "Invalid dates.";
  }
  const start = new Date(inD.getFullYear(), inD.getMonth(), inD.getDate());
  const end = new Date(outD.getFullYear(), outD.getMonth(), outD.getDate());
  if (end <= start) {
    return "Departure must be after arrival.";
  }
  return null;
}
