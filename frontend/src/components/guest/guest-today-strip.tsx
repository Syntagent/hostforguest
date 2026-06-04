"use client";

import React from "react";
import { CalendarDays, Clock, Sun } from "lucide-react";
import type { GuestGroup, GuestHostOfferingsPayload } from "@/lib/api";

function stayDayChip(guestGroup: GuestGroup): string | null {
  const inStr = guestGroup.check_in_date;
  const outStr = guestGroup.check_out_date;
  if (!inStr || !outStr) return null;
  const inD = new Date(inStr);
  const outD = new Date(outStr);
  const now = new Date();
  if (Number.isNaN(inD.getTime()) || Number.isNaN(outD.getTime())) return null;
  const dayMs = 86400000;
  const start = new Date(inD.getFullYear(), inD.getMonth(), inD.getDate());
  const end = new Date(outD.getFullYear(), outD.getMonth(), outD.getDate());
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (today < start) {
    const until = Math.ceil((start.getTime() - today.getTime()) / dayMs);
    return until === 1 ? "Arriving tomorrow" : `Arriving in ${until} days`;
  }
  if (today > end) return "Stay completed — hope you enjoyed Croatia!";
  const dayNum = Math.floor((today.getTime() - start.getTime()) / dayMs) + 1;
  const total = Math.max(1, Math.floor((end.getTime() - start.getTime()) / dayMs) + 1);
  const left = Math.ceil((end.getTime() - today.getTime()) / dayMs);
  if (left === 0) return `Day ${dayNum} of ${total} — last day!`;
  return `Day ${dayNum} of ${total} · ${left} day${left === 1 ? "" : "s"} left`;
}

export const GuestTodayStrip: React.FC<{
  guestGroup: GuestGroup;
  hostOfferings: GuestHostOfferingsPayload | null;
}> = ({ guestGroup, hostOfferings }) => {
  const dayLine = stayDayChip(guestGroup);
  const rules = hostOfferings?.stay_info?.property_rules;
  const checkIn = rules?.checkInTime;
  const checkOut = rules?.checkOutTime;
  const city = hostOfferings?.stay_info?.city?.trim();

  if (!dayLine && !checkIn && !checkOut) return null;

  return (
    <section
      className="mt-4 rounded-2xl border border-emerald-300/50 bg-emerald-50/60 p-4 shadow-sm dark:border-emerald-900/40 dark:bg-emerald-950/20"
      aria-label="Today at a glance"
      data-testid="guest-today-strip"
    >
      <div className="flex flex-wrap items-start gap-4">
        {dayLine ? (
          <div className="flex min-w-[10rem] flex-1 items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-emerald-600 text-white">
              <Sun className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800 dark:text-emerald-200">
                Today
              </p>
              <p className="mt-0.5 font-semibold text-foreground">{dayLine}</p>
              {city ? <p className="text-xs text-muted-foreground">{city}</p> : null}
            </div>
          </div>
        ) : null}
        {(checkIn || checkOut) ? (
          <div className="flex flex-wrap gap-3 text-sm">
            {checkIn ? (
              <div className="inline-flex items-center gap-1.5 rounded-xl border border-border/60 bg-background/70 px-3 py-2">
                <Clock className="h-4 w-4 text-muted-foreground" aria-hidden />
                <span>
                  <span className="text-muted-foreground">Check-in </span>
                  <span className="font-medium text-foreground">{checkIn}</span>
                </span>
              </div>
            ) : null}
            {checkOut ? (
              <div className="inline-flex items-center gap-1.5 rounded-xl border border-border/60 bg-background/70 px-3 py-2">
                <CalendarDays className="h-4 w-4 text-muted-foreground" aria-hidden />
                <span>
                  <span className="text-muted-foreground">Check-out </span>
                  <span className="font-medium text-foreground">{checkOut}</span>
                </span>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
};
