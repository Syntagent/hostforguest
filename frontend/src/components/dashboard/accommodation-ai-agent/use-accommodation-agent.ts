"use client";

import React from "react";
import {
  onboardingApi,
  type AccommodationAgentMessage,
  type AccommodationChecklistItemState,
  type AccommodationPatch,
} from "@/lib/api";
import {
  ACCOMMODATION_CHECKLIST,
  buildAccommodationChecklist,
  getNextChecklistItem,
  type AccommodationSnapshot,
} from "./accommodation-checklist";

const STORAGE_KEY = "tg_accommodation_agent_v1";

type StoredAgentState = {
  messages: AccommodationAgentMessage[];
  checklist: AccommodationChecklistItemState[];
};

export function useAccommodationAgent(snapshot: AccommodationSnapshot) {
  const [messages, setMessages] = React.useState<AccommodationAgentMessage[]>([]);
  const [checklist, setChecklist] = React.useState<AccommodationChecklistItemState[]>(() =>
    buildAccommodationChecklist(snapshot),
  );
  const [activeItemId, setActiveItemId] = React.useState<string | null>(null);
  const [pendingPatch, setPendingPatch] = React.useState<AccommodationPatch | null>(null);
  const [quickReplies, setQuickReplies] = React.useState<string[]>([]);
  const [isThinking, setIsThinking] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as StoredAgentState;
      if (Array.isArray(parsed.messages)) setMessages(parsed.messages);
      if (Array.isArray(parsed.checklist)) {
        const rebuilt = buildAccommodationChecklist(snapshot, parsed.checklist);
        setChecklist(rebuilt);
        setActiveItemId(getNextChecklistItem(rebuilt)?.id ?? null);
      }
    } catch {
      /* ignore corrupt local agent state */
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- hydrate once

  React.useEffect(() => {
    setChecklist((current) => {
      const rebuilt = buildAccommodationChecklist(snapshot, current);
      setActiveItemId((currentId) => currentId ?? getNextChecklistItem(rebuilt)?.id ?? null);
      return rebuilt;
    });
  }, [snapshot]);

  React.useEffect(() => {
    if (messages.length > 0) return;
    const initialChecklist = buildAccommodationChecklist(snapshot, checklist);
    const next = getNextChecklistItem(initialChecklist);
    setMessages([
      {
        role: "assistant",
        content: `Your Stay profile is getting stronger. Let us start with ${next?.label ?? "the next missing fact"}: ${
          ACCOMMODATION_CHECKLIST.find((item) => item.id === next?.id)?.prompt ?? "What should guests know first?"
        }`,
      },
    ]);
    setActiveItemId(next?.id ?? null);
  }, [checklist, messages.length, snapshot]);

  React.useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, checklist }));
  }, [messages, checklist]);

  const sendMessage = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || isThinking) return;
    setError(null);
    setIsThinking(true);
    const userMessage: AccommodationAgentMessage = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setChecklist((items) =>
      items.map((item) => (item.id === activeItemId ? { ...item, status: "in_progress" } : item)),
    );

    const response = await onboardingApi.sendAccommodationAgentMessage({
      message: trimmed,
      focused_item_id: activeItemId,
      checklist_state: checklist,
      accommodation_snapshot: snapshot as Record<string, unknown>,
      conversation_history: nextMessages.slice(-8),
    });

    if (response.success && response.data) {
      const data = response.data;
      setMessages((current) => [...current, { role: "assistant", content: data.reply }]);
      setQuickReplies(data.quick_replies ?? []);
      setPendingPatch(Object.keys(data.suggested_patch ?? {}).length > 0 ? data.suggested_patch : null);
      setChecklist((items) => {
        const updates = new Map((data.checklist_updates ?? []).map((item) => [item.id, item]));
        return items.map((item) => ({ ...item, ...(updates.get(item.id) ?? {}) }));
      });
      if (data.next_focus_id) setActiveItemId(data.next_focus_id);
    } else {
      setError(response.error || "The assistant could not answer right now.");
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "I could not reach AI right now. Add the fact manually or try again in a moment.",
        },
      ]);
    }
    setIsThinking(false);
  };

  const markPatchApplied = () => {
    if (!activeItemId) return;
    setChecklist((items) =>
      items.map((item) => (item.id === activeItemId ? { ...item, status: "draft" } : item)),
    );
    setPendingPatch(null);
  };

  const skipActiveItem = () => {
    if (!activeItemId) return;
    setChecklist((items) => {
      const updated = items.map((item) =>
        item.id === activeItemId ? { ...item, status: "skipped" as const } : item,
      );
      setActiveItemId(getNextChecklistItem(updated)?.id ?? null);
      return updated;
    });
  };

  return {
    messages,
    checklist,
    activeItemId,
    pendingPatch,
    quickReplies,
    isThinking,
    error,
    setActiveItemId,
    sendMessage,
    markPatchApplied,
    skipActiveItem,
    setPendingPatch,
  };
}

