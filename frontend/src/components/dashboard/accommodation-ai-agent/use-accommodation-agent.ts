"use client";

import React from "react";
import {
  onboardingApi,
  type AccommodationAgentAction,
  type AccommodationAgentMessage,
  type AccommodationAgentMessageResponse,
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

const PAGE_AGENT_CONTRACT = {
  page_goal:
    "Complete the Accommodation profile with only true, useful facts guests can rely on: name, type, capacity, location, GPS, story, amenities, services, specialties, languages, welcome message, photos, and rules.",
  allowed_actions: ["update_draft", "replace_draft", "move_focus", "open_fields", "ask_followup", "no_op"],
  safety_rules: [
    "Draft changes must stay pending until the host reviews and applies them.",
    "Free-text and voice replies must be interpreted from page context, not keyword matching.",
    "Move focus only when there is no unapplied draft for the current item.",
    "Use open_fields when exact structured values are better edited in the form.",
  ],
};

function formatLocation(snapshot: AccommodationSnapshot) {
  return [snapshot.address, snapshot.city, snapshot.county].filter(Boolean).join(", ");
}

function formatPropertyType(value: string | undefined) {
  const labels: Record<string, string> = {
    apartment: "Apartment",
    house: "House",
    villa: "Villa",
    room: "Private room",
    cabin: "Cabin",
  };
  return value ? labels[value] || value : "";
}

function assistantPromptFor(itemId: string | null, snapshot: AccommodationSnapshot) {
  const definition = ACCOMMODATION_CHECKLIST.find((item) => item.id === itemId);
  if (!definition) return "Pick the next missing fact from the checklist.";
  if (definition.id === "property_name") {
    return snapshot.property_name
      ? `Confirm this public property name is correct: ${snapshot.property_name}.`
      : "Add the public property name guests should see.";
  }
  if (definition.id === "property_type") {
    const propertyType = formatPropertyType(snapshot.property_type);
    return propertyType
      ? `Confirm this property type is correct: ${propertyType}.`
      : "Choose the closest property type.";
  }
  if (definition.id === "capacity") {
    const guests = Number(snapshot.max_guests || 0);
    const rooms = Number(snapshot.number_of_rooms || 0);
    return guests > 0 && rooms > 0
      ? `Confirm this capacity is correct: ${guests} guest${guests === 1 ? "" : "s"} / ${rooms} room${rooms === 1 ? "" : "s"}.`
      : "Add how many guests and rooms you can host comfortably.";
  }
  if (definition.id === "location_core") {
    const location = formatLocation(snapshot);
    return location
      ? `Confirm this location is correct: ${location}.`
      : "Add the city and full address so guest recommendations use the right place.";
  }
  if (definition.id === "gps") {
    const hasGps = typeof snapshot.latitude === "number" && typeof snapshot.longitude === "number";
    return hasGps
      ? `Confirm this map pin is correct: ${snapshot.latitude}, ${snapshot.longitude}.`
      : "Add or confirm the map pin so nearby recommendations use accurate distances.";
  }
  if (definition.id === "amenities") {
    return "Confirm amenities. Tap options below, or type anything missing.";
  }
  if (definition.id === "services") {
    return "Confirm only services you can actually provide or arrange.";
  }
  return `${definition.label}: ${definition.prompt}`;
}

function transitionPromptFor(itemId: string | null, snapshot: AccommodationSnapshot) {
  if (!itemId) return "Great. The core accommodation facts are complete.";
  return `Next, let's confirm this detail: ${assistantPromptFor(itemId, snapshot)}`;
}

/** Route free-text to the checklist item the host is actually talking about. */
function resolveFocusFromMessage(message: string, activeItemId: string | null): string | null {
  const lower = message.toLowerCase();
  if (
    /property story|location story|guest[- ]facing description|about (the )?story|in (the )?story|our story/.test(
      lower,
    ) &&
    !/property name|public name|listing name/.test(lower)
  ) {
    return "location_story";
  }
  if (/welcome message|greeting/.test(lower)) return "welcome_message";
  if (/property name|public name|listing name/.test(lower)) return "property_name";
  return activeItemId;
}

function patchHasValues(patch: AccommodationPatch | null | undefined) {
  if (!patch) return false;
  return Object.values(patch).some((value) => {
    if (Array.isArray(value)) return value.length > 0;
    return value !== undefined && value !== null && value !== "";
  });
}

function compactPatch(patch: AccommodationPatch | null | undefined) {
  if (!patch) return null;
  return Object.fromEntries(
    Object.entries(patch).filter(([, value]) => value !== undefined && value !== null && value !== ""),
  ) as AccommodationPatch;
}

function patchFromActions(actions: AccommodationAgentAction[] | undefined) {
  const draftAction = (actions || []).find(
    (action) =>
      (action.action === "update_draft" || action.action === "replace_draft") &&
      patchHasValues(action.patch),
  );
  return compactPatch(draftAction?.patch);
}

function replaceFieldsFromActions(actions: AccommodationAgentAction[] | undefined) {
  return (actions || [])
    .filter((action) => action.action === "replace_draft" && patchHasValues(action.patch))
    .flatMap((action) => Object.keys(compactPatch(action.patch) || {}));
}

export function useAccommodationAgent(snapshot: AccommodationSnapshot) {
  const [messages, setMessages] = React.useState<AccommodationAgentMessage[]>([]);
  const [checklist, setChecklist] = React.useState<AccommodationChecklistItemState[]>(() =>
    buildAccommodationChecklist(snapshot),
  );
  const [activeItemId, setActiveItemId] = React.useState<string | null>(null);
  const [pendingPatch, setPendingPatch] = React.useState<AccommodationPatch | null>(null);
  const [pendingReplaceFields, setPendingReplaceFields] = React.useState<string[]>([]);
  const [quickReplies, setQuickReplies] = React.useState<string[]>([]);
  const [requestedEditItemId, setRequestedEditItemId] = React.useState<string | null>(null);
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
      setActiveItemId((currentId) => {
        const nextItem = getNextChecklistItem(rebuilt);
        const currentItem = rebuilt.find((item) => item.id === currentId);
        const currentIndex = rebuilt.findIndex((item) => item.id === currentId);
        const nextIndex = rebuilt.findIndex((item) => item.id === nextItem?.id);
        if (
          currentItem &&
          (currentItem.status === "missing" || currentItem.status === "in_progress") &&
          currentIndex >= 0 &&
          nextIndex >= 0 &&
          currentIndex <= nextIndex
        ) {
          return currentId;
        }
        return nextItem?.id ?? null;
      });
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
        content: assistantPromptFor(next?.id ?? null, snapshot),
      },
    ]);
    setActiveItemId(next?.id ?? null);
  }, [checklist, messages.length, snapshot]);

  React.useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, checklist }));
  }, [messages, checklist]);

  React.useEffect(() => {
    setMessages((current) => {
      const first = current[0];
      if (!first || current.length !== 1 || first.role !== "assistant") return current;
      return [
        {
          ...first,
          content: assistantPromptFor(activeItemId, snapshot),
        },
        ...current.slice(1),
      ];
    });
  }, [activeItemId, snapshot]);

  const applyAgentTurn = React.useCallback(
    (data: AccommodationAgentMessageResponse, options?: { userMessage?: string }) => {
      const actionPatch = patchFromActions(data.actions);
      const nextPatch = actionPatch || compactPatch(data.suggested_patch);
      const hasSuggestedPatch = patchHasValues(nextPatch);
      setMessages((current) => {
        const next = [...current];
        if (options?.userMessage) {
          next.push({ role: "user", content: options.userMessage });
        }
        next.push({ role: "assistant", content: data.reply });
        return next;
      });
      setQuickReplies(data.quick_replies ?? []);
      setPendingPatch(hasSuggestedPatch ? nextPatch : null);
      setPendingReplaceFields(hasSuggestedPatch ? replaceFieldsFromActions(data.actions) : []);
      setChecklist((items) => {
        const updates = new Map((data.checklist_updates ?? []).map((item) => [item.id, item]));
        return items.map((item) => ({ ...item, ...(updates.get(item.id) ?? {}) }));
      });
      for (const action of data.actions || []) {
        if (action.action === "open_fields" && action.target_item_id) {
          setRequestedEditItemId(action.target_item_id);
        }
        if (!hasSuggestedPatch && action.action === "move_focus" && action.target_item_id) {
          setActiveItemId(action.target_item_id);
        }
      }
      if (hasSuggestedPatch && data.suggested_patch?.location_story) {
        setActiveItemId("location_story");
      }
      if (!hasSuggestedPatch && data.next_focus_id) setActiveItemId(data.next_focus_id);
    },
    [],
  );

  const sendMessage = async (content: string, turnContext?: Record<string, unknown>) => {
    const trimmed = content.trim();
    if (!trimmed || isThinking) return;
    setError(null);
    setIsThinking(true);
    const resolvedFocus = resolveFocusFromMessage(trimmed, activeItemId);
    if (resolvedFocus && resolvedFocus !== activeItemId) {
      setActiveItemId(resolvedFocus);
      setPendingPatch(null);
      setPendingReplaceFields([]);
    }
    const focusForTurn = resolvedFocus || activeItemId;
    const userMessage: AccommodationAgentMessage = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setChecklist((items) =>
      items.map((item) => (item.id === focusForTurn ? { ...item, status: "in_progress" } : item)),
    );

    const response = await onboardingApi.sendAccommodationAgentMessage({
      message: trimmed,
      focused_item_id: focusForTurn,
      checklist_state: checklist,
      accommodation_snapshot: {
        ...(snapshot as Record<string, unknown>),
        _agent_context: {
          ...PAGE_AGENT_CONTRACT,
          pending_patch: resolvedFocus && resolvedFocus !== activeItemId ? {} : pendingPatch || {},
          active_item_id: focusForTurn,
          checklist_state: checklist,
          ...(turnContext || {}),
        },
      },
      conversation_history: nextMessages.slice(-8),
    });

    if (response.success && response.data) {
      applyAgentTurn(response.data);
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
    const updated = checklist.map((item) => (item.id === activeItemId ? { ...item, status: "draft" as const } : item));
    const patchedSnapshot = { ...snapshot, ...(pendingPatch || {}) };
    const rebuilt = buildAccommodationChecklist(patchedSnapshot, updated);
    const next = getNextChecklistItem(rebuilt);
    setChecklist(rebuilt);
    setActiveItemId(next?.id ?? null);
    setQuickReplies([]);
    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: transitionPromptFor(next?.id ?? null, patchedSnapshot),
      },
    ]);
    setPendingPatch(null);
    setPendingReplaceFields([]);
  };

  const togglePendingPatchOption = (field: keyof AccommodationPatch, option: string) => {
    setPendingPatch((current) => {
      const currentValues = Array.isArray(current?.[field]) ? (current[field] as string[]) : [];
      const nextValues = currentValues.includes(option)
        ? currentValues.filter((item) => item !== option)
        : [...currentValues, option];
      return {
        ...(current || {}),
        [field]: nextValues,
      };
    });
    setPendingReplaceFields((current) => [...new Set([...current, field])]);
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
    pendingReplaceFields,
    quickReplies,
    requestedEditItemId,
    isThinking,
    error,
    setActiveItemId,
    sendMessage,
    applyAgentTurn,
    markPatchApplied,
    skipActiveItem,
    setPendingPatch,
    togglePendingPatchOption,
    consumeRequestedEdit: () => setRequestedEditItemId(null),
  };
}

