"use client";

import React from "react";
import Image from "next/image";
import {
  BedDouble,
  Clock,
  Globe,
  Home,
  MapPin,
  Phone,
  Shield,
  Sparkles,
  Tag,
  Wifi,
  Wrench,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { GuestGroup, GuestHostOfferingsPayload, GuestPropertyRules } from "@/lib/api";
import { cn } from "@/lib/utils";

const EMERGENCY_NUMBERS = [
  { label: "Emergency (EU)", number: "112", note: "Police, fire, ambulance" },
  { label: "Police", number: "192", note: "Non-emergency police" },
  { label: "Ambulance", number: "194", note: "Medical emergency" },
  { label: "Fire brigade", number: "193", note: "Fire emergency" },
  { label: "Road assistance", number: "1987", note: "HAK roadside help" },
];

function formatLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function partnerLabel(partner: string | Record<string, unknown>): string {
  if (typeof partner === "string") return partner;
  const name = partner.name ?? partner.title ?? partner.business_name;
  return typeof name === "string" ? name : "Local partner";
}

function partnerDescription(partner: string | Record<string, unknown>): string | null {
  if (typeof partner === "string") return null;
  const desc = partner.description ?? partner.note ?? partner.summary;
  return typeof desc === "string" ? desc : null;
}

function offerLabel(offer: string | Record<string, unknown>): string {
  if (typeof offer === "string") return offer;
  const title = offer.title ?? offer.name ?? offer.label;
  return typeof title === "string" ? title : "Special offer";
}

export const GuestStayTab: React.FC<{
  guestGroup: GuestGroup;
  hostOfferings: GuestHostOfferingsPayload | null;
  onNavigateMaintenance: () => void;
  onNavigateDiscover: () => void;
}> = ({ guestGroup, hostOfferings, onNavigateMaintenance, onNavigateDiscover }) => {
  const si = hostOfferings?.stay_info;
  const hi = hostOfferings?.host_info;
  const rules: GuestPropertyRules = si?.property_rules || {};
  const gallery = (si?.gallery_images || []).filter(
    (url): url is string => typeof url === "string" && url.trim().length > 0
  );
  const amenities = (si?.amenities || []).filter(Boolean);
  const services = (si?.services_offered || []).filter(Boolean);
  const languages = (hi?.languages || hostOfferings?.guest_services?.supported_languages || []).filter(
    Boolean
  ) as string[];
  const partners = hostOfferings?.trusted_partners || [];
  const offers = hostOfferings?.special_offers || [];
  const propertyName = si?.property_name?.trim() || "Your accommodation";
  const city = si?.city?.trim();

  return (
    <div className="space-y-4" data-testid="guest-stay-tab">
      <div className="section-shell px-4 py-5 md:px-6">
        <h2 className="text-2xl font-semibold">Your stay</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Everything practical for {guestGroup.group_name?.trim() || "your group"} at the property —
          rules, amenities, services, and who to call.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Home className="h-5 w-5 text-primary" aria-hidden />
            {propertyName}
          </CardTitle>
          <CardDescription>
            {[si?.property_type, city, si?.region].filter(Boolean).join(" · ") || "Property details"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {si?.address?.trim() ? (
            <p className="flex items-start gap-2 text-foreground">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
              {si.address.trim()}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-3 text-muted-foreground">
            {si?.number_of_rooms ? (
              <span className="inline-flex items-center gap-1">
                <BedDouble className="h-4 w-4" aria-hidden />
                {si.number_of_rooms} room{si.number_of_rooms === 1 ? "" : "s"}
              </span>
            ) : null}
            {si?.max_guests ? (
              <span>Up to {si.max_guests} guest{si.max_guests === 1 ? "" : "s"}</span>
            ) : null}
          </div>
          {hi?.name ? (
            <p className="text-foreground">
              <span className="font-medium">Host:</span> {hi.name}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {gallery.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Photos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
              {gallery.slice(0, 9).map((url, i) => (
                <div key={`${url.slice(0, 40)}-${i}`} className="relative aspect-[4/3] overflow-hidden rounded-xl bg-muted">
                  <Image src={url} alt="" fill className="object-cover" unoptimized={url.startsWith("data:")} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {(rules.checkInTime || rules.checkOutTime || rules.cancellationPolicy) ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Clock className="h-5 w-5 text-primary" aria-hidden />
              Check-in &amp; check-out
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {rules.checkInTime ? (
              <div className="rounded-xl border border-border/70 bg-muted/30 px-3 py-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Check-in from</p>
                <p className="mt-1 font-semibold text-foreground">{rules.checkInTime}</p>
              </div>
            ) : null}
            {rules.checkOutTime ? (
              <div className="rounded-xl border border-border/70 bg-muted/30 px-3 py-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Check-out by</p>
                <p className="mt-1 font-semibold text-foreground">{rules.checkOutTime}</p>
              </div>
            ) : null}
            {rules.cancellationPolicy ? (
              <p className="sm:col-span-2 text-sm text-muted-foreground">{rules.cancellationPolicy}</p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {(rules.wifiName || rules.wifiPassword) ? (
        <Card className="border-sky-200/70 bg-sky-50/40 dark:border-sky-900/40 dark:bg-sky-950/15">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Wifi className="h-5 w-5 text-sky-700 dark:text-sky-300" aria-hidden />
              WiFi
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {rules.wifiName ? (
              <p>
                <span className="font-medium text-foreground">Network:</span> {rules.wifiName}
              </p>
            ) : null}
            {rules.wifiPassword ? (
              <p>
                <span className="font-medium text-foreground">Password:</span>{" "}
                <code className="rounded bg-background/80 px-1.5 py-0.5">{rules.wifiPassword}</code>
              </p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {amenities.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Amenities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {amenities.map((a) => (
                <span
                  key={a}
                  className="rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs font-medium text-foreground"
                >
                  {formatLabel(a)}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {services.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-primary" aria-hidden />
              Host can help with
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-inside list-disc space-y-1 text-sm text-foreground/90">
              {services.map((s) => (
                <li key={s}>{formatLabel(s)}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {(rules.houseRules?.length || rules.additionalPolicies?.length) ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">House rules</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {(rules.houseRules || []).map((rule, i) => (
              <p key={`hr-${i}`} className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2">
                {rule}
              </p>
            ))}
            {(rules.additionalPolicies || []).length > 0 ? (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Good to know
                </p>
                <ul className="list-inside list-disc space-y-1 text-muted-foreground">
                  {(rules.additionalPolicies || []).map((p, i) => (
                    <li key={`ap-${i}`}>{p}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {languages.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Globe className="h-5 w-5 text-primary" aria-hidden />
              Languages
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground">{languages.map((l) => l.toUpperCase()).join(", ")}</p>
          </CardContent>
        </Card>
      ) : null}

      {offers.length > 0 ? (
        <Card className="border-amber-200/70 bg-amber-50/30 dark:border-amber-900/40 dark:bg-amber-950/15">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Tag className="h-5 w-5 text-amber-700 dark:text-amber-300" aria-hidden />
              Special offers
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {offers.map((offer, i) => (
              <p key={i} className="rounded-lg border border-amber-200/50 bg-background/70 px-3 py-2 text-sm">
                {offerLabel(offer)}
              </p>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {partners.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Trusted local partners</CardTitle>
            <CardDescription>Businesses your host recommends</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {partners.map((partner, i) => {
              const desc = partnerDescription(partner);
              return (
                <div key={i} className="rounded-xl border border-border/60 bg-background/60 p-3">
                  <p className="font-semibold text-foreground">{partnerLabel(partner)}</p>
                  {desc ? <p className="mt-1 text-sm text-muted-foreground">{desc}</p> : null}
                </div>
              );
            })}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className="h-5 w-5 text-primary" aria-hidden />
            Emergency &amp; help
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {rules.emergencyNote?.trim() ? (
            <p className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-sm text-foreground">
              {rules.emergencyNote.trim()}
            </p>
          ) : null}
          <ul className="grid gap-2 sm:grid-cols-2">
            {EMERGENCY_NUMBERS.map((row) => (
              <li
                key={row.number}
                className="flex items-start justify-between gap-2 rounded-xl border border-border/70 bg-muted/20 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium text-foreground">{row.label}</p>
                  <p className="text-xs text-muted-foreground">{row.note}</p>
                </div>
                <a
                  href={`tel:${row.number}`}
                  className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-primary/10 px-2.5 py-1.5 text-sm font-semibold text-primary"
                >
                  <Phone className="h-3.5 w-3.5" aria-hidden />
                  {row.number}
                </a>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button type="button" variant="outline" size="sm" onClick={onNavigateMaintenance}>
              <Wrench className="mr-1.5 h-4 w-4" aria-hidden />
              Report property issue
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={onNavigateDiscover}>
              Explore nearby
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
