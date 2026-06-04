"use client";

import React, { useCallback, useState } from "react";
import { Bot, MessageCircle, Send, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { guestGroupsApi, type GuestHostOfferingsPayload } from "@/lib/api";
import { cn } from "@/lib/utils";
import { guestCopy, type GuestLocale } from "@/lib/guest-i18n";

type ChatTurn = {
  role: "guest" | "assistant" | "host-note";
  text: string;
};

type GuestTab =
  | "welcome"
  | "stay"
  | "events"
  | "recommendations"
  | "itinerary"
  | "map"
  | "maintenance";

export const GuestAssistantFab: React.FC<{
  accessCode: string;
  guestName?: string | null;
  guestLocale?: GuestLocale;
  hostOfferings: GuestHostOfferingsPayload | null;
  activeTab: GuestTab;
}> = ({ accessCode, guestName, guestLocale = "en", hostOfferings, activeTab }) => {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"assistant" | "host">("assistant");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const responseHint =
    hostOfferings?.contact?.response_time || "Usually within 2 hours";
  const aiAvailable = hostOfferings?.contact?.ai_assistant_available !== false;

  const pushTurn = useCallback((turn: ChatTurn) => {
    setTurns((prev) => [...prev, turn]);
  }, []);

  const send = async (overrideText?: string) => {
    const message = (overrideText ?? text).trim();
    if (!message || busy) return;
    setBusy(true);
    pushTurn({ role: "guest", text: message });
    setText("");

    try {
      if (mode === "assistant" && aiAvailable) {
        const r = await guestGroupsApi.askAssistant(accessCode, {
          message,
          guest_name: guestName || undefined,
        });
        if (!r.success) {
          pushTurn({ role: "assistant", text: r.error || "Could not reach the assistant. Try again." });
        } else {
          pushTurn({ role: "assistant", text: r.data?.message || "Here to help!" });
          setSuggestions(r.data?.suggestions || []);
        }
      } else {
        const r = await guestGroupsApi.sendHostMessage(accessCode, {
          message,
          type: mode === "host" ? "general" : "question",
          guest_name: guestName || undefined,
        });
        if (!r.success) {
          pushTurn({ role: "host-note", text: r.error || "Could not send. Try again later." });
        } else {
          pushTurn({
            role: r.data?.response_type === "ai_assistant" ? "assistant" : "host-note",
            text: r.data?.message || "Sent to your host.",
          });
          setSuggestions(r.data?.suggestions || []);
        }
      }
    } finally {
      setBusy(false);
    }
  };

  if (activeTab === "maintenance") return null;

  return (
    <>
      <button
        type="button"
        className="fixed bottom-[calc(6rem+env(safe-area-inset-bottom))] right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105 md:bottom-8"
        onClick={() => {
          setOpen(true);
          if (turns.length === 0 && aiAvailable) {
            setSuggestions([
              guestCopy(guestLocale, "assistantEventsSuggestion"),
              "Where should we eat nearby?",
              "How do check-in and house rules work?",
            ]);
          }
        }}
        aria-label="Open guest assistant"
        data-testid="guest-assistant-fab"
      >
        <Bot className="h-7 w-7" aria-hidden />
      </button>
      {open ? (
        <div className="fixed inset-0 z-[110] flex items-end justify-center sm:items-center sm:p-4">
          <button
            type="button"
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            aria-label="Close"
            onClick={() => setOpen(false)}
          />
          <div className="relative z-[111] flex max-h-[min(88vh,640px)] w-full max-w-md flex-col rounded-t-3xl border border-border bg-background shadow-2xl sm:rounded-3xl">
            <div className="border-b border-border px-5 py-4">
              <h3 className="text-lg font-semibold text-foreground">Guest assistant</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Ask about your stay, local tips, or message your host. {responseHint}.
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium",
                    mode === "assistant"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  )}
                  onClick={() => setMode("assistant")}
                >
                  <Bot className="mr-1 inline h-3.5 w-3.5" aria-hidden />
                  AI guide
                </button>
                <button
                  type="button"
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium",
                    mode === "host"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  )}
                  onClick={() => setMode("host")}
                >
                  <MessageCircle className="mr-1 inline h-3.5 w-3.5" aria-hidden />
                  Message host
                </button>
              </div>
            </div>

            <div className="min-h-[12rem] flex-1 space-y-3 overflow-y-auto px-5 py-4">
              {turns.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Try a quick question — or pick a suggestion below.
                </p>
              ) : (
                turns.map((turn, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex gap-2 text-sm",
                      turn.role === "guest" ? "justify-end" : "justify-start"
                    )}
                  >
                    {turn.role !== "guest" ? (
                      turn.role === "assistant" ? (
                        <Bot className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                      ) : (
                        <MessageCircle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                      )
                    ) : null}
                    <p
                      className={cn(
                        "max-w-[85%] rounded-2xl px-3 py-2",
                        turn.role === "guest"
                          ? "bg-primary text-primary-foreground"
                          : "border border-border bg-muted/40 text-foreground"
                      )}
                    >
                      {turn.text}
                    </p>
                    {turn.role === "guest" ? (
                      <User className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                    ) : null}
                  </div>
                ))
              )}
            </div>

            {suggestions.length > 0 ? (
              <div className="flex gap-2 overflow-x-auto border-t border-border px-5 py-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="shrink-0 rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
                    onClick={() => void send(s)}
                    disabled={busy}
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : null}

            <div className="border-t border-border p-4">
              <div className="flex gap-2">
                <textarea
                  className="min-h-[44px] flex-1 rounded-xl border border-input bg-background px-3 py-2 text-sm"
                  placeholder={
                    mode === "host"
                      ? "Message for your host…"
                      : "Ask about places, rules, or today…"
                  }
                  value={text}
                  rows={2}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void send();
                    }
                  }}
                />
                <Button
                  type="button"
                  size="icon"
                  disabled={busy || !text.trim()}
                  aria-label="Send"
                  onClick={() => void send()}
                >
                  <Send className="h-4 w-4" aria-hidden />
                </Button>
              </div>
              <Button type="button" variant="ghost" size="sm" className="mt-2 w-full" onClick={() => setOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};
