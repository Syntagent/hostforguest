"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cleaningApi, CleaningProvider } from "@/lib/api";
import { Copy, ExternalLink, Loader2, Mail, Phone, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

function waLink(phone: string | null | undefined): string | null {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 8) return null;
  return `https://wa.me/${digits}`;
}

export const CleaningTab: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [providers, setProviders] = useState<CleaningProvider[]>([]);
  const [myCleaners, setMyCleaners] = useState<CleaningProvider[]>([]);
  const [checkouts, setCheckouts] = useState<
    { guest_group_id: string; group_name?: string | null; check_out_date: string }[]
  >([]);
  const [ranked, setRanked] = useState<CleaningProvider[]>([]);
  const [discMeta, setDiscMeta] = useState<{ disclaimer?: string; ai_used?: boolean }>({});
  const [bookings, setBookings] = useState<
    {
      id: string;
      partner_id: string | null;
      status: string;
      service_date: string | null;
      booking_details: Record<string, unknown>;
    }[]
  >([]);
  const [feeDisclaimer, setFeeDisclaimer] = useState("");
  const [selected, setSelected] = useState<CleaningProvider | null>(null);
  const [message, setMessage] = useState("");
  const [intent, setIntent] = useState<"turnover" | "deep_clean">("turnover");
  const [checkoutId, setCheckoutId] = useState<string>("");
  const [serviceDate, setServiceDate] = useState<string>("");
  const [msgCtx, setMsgCtx] = useState<{
    property_name?: string | null;
    address?: string | null;
    city?: string | null;
    county?: string | null;
    next_checkout?: {
      guest_group_id: string;
      group_name?: string | null;
      check_out_date: string;
    } | null;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [p, m, c, b, ctx] = await Promise.all([
      cleaningApi.getProviders(),
      cleaningApi.getMyCleaners(),
      cleaningApi.getUpcomingCheckouts(),
      cleaningApi.getBookings(),
      cleaningApi.getMessageContext(),
    ]);
    if (p.success && p.data) {
      setProviders(p.data.providers || []);
      setFeeDisclaimer(p.data.disclaimer_indicative_fees || "");
    }
    if (m.success && m.data) {
      setMyCleaners((m.data.cleaners || []).map((x) => x.partner));
    }
    if (c.success && c.data) setCheckouts(c.data.checkouts || []);
    if (b.success && b.data) setBookings(b.data.bookings || []);
    if (ctx.success && ctx.data) setMsgCtx(ctx.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedCheckout = useMemo(
    () => checkouts.find((x) => x.guest_group_id === checkoutId),
    [checkouts, checkoutId]
  );

  const buildTemplate = useCallback(() => {
    const lines: string[] = [];
    lines.push(intent === "deep_clean" ? "Deep clean request" : "Turnover clean request");
    if (msgCtx?.property_name) lines.push(`Property: ${msgCtx.property_name}`);
    const loc = [msgCtx?.address, msgCtx?.city, msgCtx?.county].filter(Boolean).join(", ");
    if (loc) lines.push(`Location: ${loc}`);
    if (serviceDate) lines.push(`Requested date: ${serviceDate}`);
    if (selectedCheckout) {
      lines.push(`Guest checkout: ${selectedCheckout.check_out_date}`);
      if (selectedCheckout.group_name) lines.push(`Stay / group: ${selectedCheckout.group_name}`);
    } else if (msgCtx?.next_checkout) {
      lines.push(`Next guest checkout: ${msgCtx.next_checkout.check_out_date}`);
      if (msgCtx.next_checkout.group_name) lines.push(`Group: ${msgCtx.next_checkout.group_name}`);
    }
    lines.push("Please confirm price, time window, and what is included (linen, supplies).");
    lines.push("Thank you.");
    setMessage(lines.join("\n"));
  }, [intent, serviceDate, selectedCheckout, msgCtx]);

  const runDiscover = async () => {
    const r = await cleaningApi.discover({ intent });
    if (r.success && r.data) {
      setRanked(r.data.ranked || []);
      setDiscMeta({ disclaimer: r.data.disclaimer, ai_used: r.data.ai_used });
    }
  };

  const runDraft = async () => {
    if (!selected) return;
    const r = await cleaningApi.draftMessage({
      partner_id: selected.id,
      intent,
      service_date: serviceDate || undefined,
      guest_group_id: checkoutId || undefined,
      language: "hr",
    });
    if (r.success && r.data?.draft) setMessage(r.data.draft);
  };

  const copyMsg = async () => {
    try {
      await navigator.clipboard.writeText(message);
    } catch {
      /* ignore */
    }
  };

  const linkCleaner = async (id: string) => {
    await cleaningApi.linkCleaner(id, {});
    void load();
  };

  const unlinkCleaner = async (id: string) => {
    await cleaningApi.unlinkCleaner(id);
    void load();
  };

  const createBooking = async () => {
    if (!selected) return;
    const body: {
      partner_id: string;
      guest_group_id?: string;
      notes?: string;
      intent: string;
      service_date?: string;
    } = {
      partner_id: selected.id,
      intent,
      notes: message.slice(0, 500) || undefined,
    };
    if (checkoutId) body.guest_group_id = checkoutId;
    if (serviceDate) body.service_date = `${serviceDate}T12:00:00`;
    const r = await cleaningApi.createBooking(body);
    if (r.success) void load();
  };

  const markCompleted = async (id: string) => {
    await cleaningApi.patchBookingStatus(id, "completed");
    void load();
  };

  const sendFeedback = async (id: string, rating: number) => {
    await cleaningApi.postFeedback(id, rating, "");
    void load();
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading cleaning partners...
      </div>
    );
  }

  const showList = ranked.length > 0 ? ranked : providers;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Cleaning & turnover</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Connect with cleaners, use AI-assisted shortlists (directory only), draft a message, and track simple
          requests. Fees shown are indicative — always confirm with the provider.
        </p>
        {feeDisclaimer ? <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">{feeDisclaimer}</p> : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">1. Upcoming check-outs</CardTitle>
          <CardDescription>Prefill turnover timing from guest stays.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {checkouts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No upcoming check-outs with dates.</p>
          ) : (
            <select
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={checkoutId}
              onChange={(e) => setCheckoutId(e.target.value)}
            >
              <option value="">Select stay (optional)</option>
              {checkouts.map((c) => (
                <option key={c.guest_group_id} value={c.guest_group_id}>
                  {c.group_name || "Guests"} — out {c.check_out_date}
                </option>
              ))}
            </select>
          )}
          <input
            type="date"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={serviceDate}
            onChange={(e) => setServiceDate(e.target.value)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base">2. Find cleaners</CardTitle>
            <CardDescription>Browse directory or run AI ranking on the same list.</CardDescription>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => void runDiscover()}>
            <Sparkles className="mr-1 h-4 w-4" />
            AI rank
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {discMeta.disclaimer ? (
            <p className="text-xs text-muted-foreground">{discMeta.disclaimer}</p>
          ) : null}
          {discMeta.ai_used != null ? (
            <p className="text-xs text-muted-foreground">AI used: {String(discMeta.ai_used)}</p>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2">
            {showList.map((pr) => (
              <div
                key={pr.id}
                className={`cursor-pointer rounded-lg border p-3 transition hover:bg-muted/40 ${
                  selected?.id === pr.id ? "border-primary ring-1 ring-primary" : ""
                }`}
                onClick={() => setSelected(pr)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(pr);
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium">{pr.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {pr.city}
                      {pr.price_range ? ` · ${pr.price_range}` : ""}
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      void linkCleaner(pr.id);
                    }}
                  >
                    Save
                  </Button>
                </div>
                {pr.ai_why ? <p className="mt-2 text-xs text-muted-foreground">{pr.ai_why}</p> : null}
                {pr.rate_card && Object.keys(pr.rate_card).length > 0 ? (
                  <pre className="mt-2 max-h-24 overflow-auto rounded bg-muted/50 p-2 text-[10px] leading-tight">
                    {JSON.stringify(pr.rate_card, null, 0)}
                  </pre>
                ) : null}
                {pr.price_notes ? <p className="mt-1 text-xs">{pr.price_notes}</p> : null}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">3. My saved cleaners</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {myCleaners.length === 0 ? (
            <p className="text-sm text-muted-foreground">None yet — use Save on a card above.</p>
          ) : (
            myCleaners.map((pr) => (
              <div key={pr.id} className="flex items-center gap-2 rounded-full border px-3 py-1 text-sm">
                <span>{pr.name}</span>
                <button
                  type="button"
                  className="text-xs text-destructive underline"
                  onClick={() => void unlinkCleaner(pr.id)}
                >
                  remove
                </button>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {selected ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">4. Contact — {selected.name}</CardTitle>
            <CardDescription>Review message, then open email, phone, or WhatsApp.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <select
                className="rounded-md border border-input bg-background px-2 py-1 text-sm"
                value={intent}
                onChange={(e) => setIntent(e.target.value as "turnover" | "deep_clean")}
              >
                <option value="turnover">Turnover clean</option>
                <option value="deep_clean">Deep clean</option>
              </select>
              <Button type="button" variant="outline" size="sm" onClick={() => buildTemplate()}>
                Template
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => void runDraft()}>
                <Sparkles className="mr-1 h-4 w-4" />
                AI draft
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => void copyMsg()}>
                <Copy className="mr-1 h-4 w-4" />
                Copy
              </Button>
            </div>
            <textarea
              className="min-h-[120px] w-full rounded-md border border-input bg-background p-3 text-sm"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Your message to the cleaner..."
            />
            <div className="flex flex-wrap gap-2">
              {selected.email ? (
                <a
                  className={cn(
                    "inline-flex items-center gap-1 rounded-2xl border-2 border-primary/35 bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90",
                  )}
                  href={`mailto:${encodeURIComponent(selected.email)}?subject=${encodeURIComponent("Cleaning request")}&body=${encodeURIComponent(message)}`}
                >
                  <Mail className="h-4 w-4" />
                  Email
                </a>
              ) : null}
              {selected.phone ? (
                <a
                  className={cn(
                    "inline-flex items-center gap-1 rounded-2xl border-2 border-primary/35 bg-white/80 px-3 py-1.5 text-sm font-semibold text-primary hover:bg-primary hover:text-primary-foreground",
                  )}
                  href={`tel:${selected.phone}`}
                >
                  <Phone className="h-4 w-4" />
                  Call
                </a>
              ) : null}
              {waLink(selected.phone) ? (
                <a
                  className={cn(
                    "inline-flex items-center gap-1 rounded-2xl border-2 border-primary/35 bg-white/80 px-3 py-1.5 text-sm font-semibold text-primary hover:bg-primary hover:text-primary-foreground",
                  )}
                  href={waLink(selected.phone) || "#"}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink className="h-4 w-4" />
                  WhatsApp
                </a>
              ) : null}
              <Button type="button" variant="secondary" size="sm" onClick={() => void createBooking()}>
                Log request
              </Button>
            </div>
            {typeof selected.commission_rate === "number" ? (
              <p className="text-xs text-muted-foreground">
                Platform commission field on file: {(selected.commission_rate * 100).toFixed(0)}% (confirm with
                provider).
              </p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">5. Requests & feedback</CardTitle>
          <CardDescription>Mark completed, then rate (once per request).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {bookings.length === 0 ? (
            <p className="text-sm text-muted-foreground">No logged requests yet.</p>
          ) : (
            bookings.map((b) => {
              const fb = (b.booking_details as { host_feedback?: unknown }).host_feedback as
                | { rating?: number }
                | undefined;
              return (
                <div key={b.id} className="rounded-md border p-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span>
                      {b.service_date || "Date TBC"} — <strong>{b.status}</strong>
                    </span>
                    {b.status === "pending" || b.status === "confirmed" ? (
                      <Button type="button" size="sm" variant="outline" onClick={() => void markCompleted(b.id)}>
                        Mark completed
                      </Button>
                    ) : null}
                  </div>
                  {b.status === "completed" && !fb ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                      <span className="text-xs text-muted-foreground">Rate:</span>
                      {[1, 2, 3, 4, 5].map((n) => (
                        <Button key={n} type="button" size="sm" variant="ghost" onClick={() => void sendFeedback(b.id, n)}>
                          {n}★
                        </Button>
                      ))}
                    </div>
                  ) : null}
                  {fb?.rating ? <p className="mt-1 text-xs text-muted-foreground">Thanks — rated {fb.rating}★</p> : null}
                </div>
              );
            })
          )}
        </CardContent>
      </Card>
    </div>
  );
};