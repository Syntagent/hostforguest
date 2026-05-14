"use client";

import React, { useEffect } from "react";
import { X, MapPin, Clock, Ticket, Mountain, Star, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  mapsUrlForAttraction,
  openAttractionInMaps,
  type Attraction,
  type Recommendation,
} from "@/lib/api";
import { cn } from "@/lib/utils";

function formatOpeningHours(hours: Record<string, string> | undefined): string[] {
  if (!hours || typeof hours !== "object") return [];
  return Object.entries(hours)
    .filter(([, v]) => v && String(v).trim())
    .map(([k, v]) => `${k}: ${v}`);
}

function monthName(m: number): string {
  return new Date(2000, m - 1, 1).toLocaleString(undefined, { month: "short" });
}

export interface AttractionDetailSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  recommendation: Recommendation | null;
}

export const AttractionDetailSheet: React.FC<AttractionDetailSheetProps> = ({
  open,
  onOpenChange,
  recommendation,
}) => {
  const a: Attraction | undefined = recommendation?.attraction;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  if (!open || !recommendation) return null;

  const gallery = [
    a?.featured_image_url,
    ...(Array.isArray(a?.image_gallery) ? a!.image_gallery! : []),
  ].filter((x): x is string => typeof x === "string" && x.trim().length > 0);

  const hoursLines = formatOpeningHours(a?.opening_hours);
  const contact = a?.contact_info && typeof a.contact_info === "object" ? a.contact_info : null;

  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center sm:items-center sm:p-4">
      <button
        type="button"
        aria-label="Close details"
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="attraction-detail-title"
        className={cn(
          "relative z-[101] flex max-h-[min(92vh,900px)] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl border border-border bg-background shadow-2xl",
          "sm:max-h-[85vh] sm:rounded-3xl"
        )}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {a?.category ? `${a.category}` : "Place"}
          </p>
          <button
            type="button"
            className="rounded-full p-2 text-muted-foreground hover:bg-muted"
            onClick={() => onOpenChange(false)}
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {gallery[0] ? (
            <div className="relative aspect-video w-full bg-muted">
              <img
                src={gallery[0]}
                alt={a?.name || ""}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            </div>
          ) : null}

          <div className="space-y-4 p-4">
            <div>
              <h2 id="attraction-detail-title" className="text-xl font-bold text-foreground">
                {a?.name || "Place"}
              </h2>
              {(a?.city || a?.address || a?.location) && (
                <p className="mt-1 flex items-start gap-1.5 text-sm text-muted-foreground">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                  <span>
                    {[a?.location, a?.address, a?.city].filter(Boolean).join(" · ")}
                  </span>
                </p>
              )}
            </div>

            {recommendation.personalization_factors &&
            recommendation.personalization_factors.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {recommendation.personalization_factors.map((f, i) => (
                  <span
                    key={i}
                    className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
                  >
                    {f}
                  </span>
                ))}
              </div>
            ) : null}

            <div className="rounded-2xl bg-primary/10 p-3">
              <p className="text-sm font-semibold text-primary">Why it fits you</p>
              <p className="mt-1 text-sm text-foreground/90">{recommendation.reason}</p>
            </div>

            {a?.description?.trim() ? (
              <p className="text-sm leading-relaxed text-muted-foreground">{a.description}</p>
            ) : null}

            {a?.host_personal_tip?.trim() ? (
              <div className="rounded-2xl border border-amber-200/80 bg-amber-50 p-3 dark:border-amber-900/50 dark:bg-amber-950/30">
                <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">
                  Your host&apos;s tip
                </p>
                <p className="mt-1 text-sm text-amber-950/90 dark:text-amber-50/90">
                  {a.host_personal_tip}
                </p>
              </div>
            ) : null}

            {a?.host_insider_info?.trim() ? (
              <div>
                <p className="text-sm font-semibold text-foreground">Insider info</p>
                <p className="mt-1 text-sm text-muted-foreground">{a.host_insider_info}</p>
              </div>
            ) : null}

            {a?.host_story?.trim() ? (
              <div>
                <p className="text-sm font-semibold text-foreground">The story</p>
                <p className="mt-1 text-sm text-muted-foreground">{a.host_story}</p>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
              {a?.host_favorite_time?.trim() ? (
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-4 w-4" aria-hidden />
                  {a.host_favorite_time}
                </span>
              ) : null}
              {a?.host_recommended_duration?.trim() ? (
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-4 w-4" aria-hidden />
                  {a.host_recommended_duration}
                </span>
              ) : null}
            </div>

            {(a?.admission_fee || a?.cost_estimate) && (
              <p className="inline-flex items-center gap-2 text-sm">
                <Ticket className="h-4 w-4 text-muted-foreground" aria-hidden />
                <span className="font-medium text-foreground">
                  {a.admission_fee || a.cost_estimate}
                </span>
              </p>
            )}

            {(a?.difficulty_level || a?.duration_hours != null) && (
              <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                <Mountain className="h-4 w-4" aria-hidden />
                {[a.difficulty_level, a.duration_hours != null ? `${a.duration_hours}h` : null]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}

            {a?.seasonal_notes?.trim() || (a?.best_months && a.best_months.length > 0) ? (
              <div className="rounded-xl border border-border bg-muted/40 p-3 text-sm">
                <p className="font-medium text-foreground">Seasonal</p>
                {a.best_months && a.best_months.length > 0 ? (
                  <p className="mt-1 text-muted-foreground">
                    Best: {a.best_months.map(monthName).join(", ")}
                  </p>
                ) : null}
                {a?.seasonal_notes?.trim() ? (
                  <p className="mt-1 text-muted-foreground">{a.seasonal_notes}</p>
                ) : null}
              </div>
            ) : null}

            {hoursLines.length > 0 ? (
              <div>
                <p className="text-sm font-semibold text-foreground">Opening hours</p>
                <ul className="mt-1 list-inside list-disc text-sm text-muted-foreground">
                  {hoursLines.slice(0, 14).map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {contact && Object.keys(contact).length > 0 ? (
              <div className="space-y-1 text-sm">
                <p className="font-semibold text-foreground">Contact</p>
                {Object.entries(contact).map(([k, v]) => (
                  <p key={k} className="text-muted-foreground">
                    <span className="capitalize">{k}: </span>
                    {String(v)}
                  </p>
                ))}
              </div>
            ) : null}

            {(a?.website || a?.phone_number) && !contact ? (
              <div className="flex flex-wrap gap-2 text-sm">
                {a.phone_number ? (
                  <a
                    href={`tel:${a.phone_number}`}
                    className="text-primary underline-offset-2 hover:underline"
                  >
                    {a.phone_number}
                  </a>
                ) : null}
                {a.website ? (
                  <a
                    href={a.website.startsWith("http") ? a.website : `https://${a.website}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline"
                  >
                    Website <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                ) : null}
              </div>
            ) : null}

            {(a?.average_rating != null || a?.rating != null) && (
              <p className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
                <Star className="h-4 w-4 text-amber-500" aria-hidden />
                {(a.average_rating ?? a.rating)?.toFixed?.(1) ?? a.rating}
                {a.review_count != null || a.user_ratings_total != null ? (
                  <span>
                    ({a.review_count ?? a.user_ratings_total}{" "}
                    {(a.review_count ?? a.user_ratings_total) === 1 ? "review" : "reviews"})
                  </span>
                ) : null}
              </p>
            )}

            {gallery.length > 1 ? (
              <div className="flex gap-2 overflow-x-auto pb-1">
                {gallery.slice(1, 8).map((url, i) => (
                  <img
                    key={i}
                    src={url}
                    alt=""
                    className="h-16 w-24 shrink-0 rounded-lg object-cover"
                    loading="lazy"
                  />
                ))}
              </div>
            ) : null}
          </div>
        </div>

        <div className="border-t border-border bg-background p-4">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              className="flex-1 sm:flex-none"
              disabled={!mapsUrlForAttraction(a)}
              onClick={() => openAttractionInMaps(a)}
            >
              Directions
            </Button>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
