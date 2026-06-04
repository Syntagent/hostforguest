"use client";

import React from "react";
import { Info, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AccommodationPatch } from "@/lib/api";
import type { AccommodationSnapshot } from "./accommodation-checklist";
import { AgentChecklist } from "./agent-checklist";
import { AgentComposer } from "./agent-composer";
import { AgentMessageList } from "./agent-message-list";
import { HorizontalChipScroller } from "./horizontal-chip-scroller";
import { useAccommodationAgent } from "./use-accommodation-agent";

type AccommodationAiAgentPanelProps = {
  snapshot: AccommodationSnapshot;
  voiceEnabled?: boolean;
  onApplyPatch: (patch: AccommodationPatch, options?: { replaceFields?: string[] }) => void;
  onEnhanceAll: () => void;
  onEditMissing?: (id: string) => void;
};

function patchPreview(patch: AccommodationPatch) {
  return Object.entries(patch).filter(([, value]) => {
    if (Array.isArray(value)) return value.length > 0;
    return value !== undefined && value !== null && value !== "";
  });
}

type PatchOption = {
  label: string;
  patch: AccommodationPatch;
};

const PROPERTY_TYPE_OPTIONS: PatchOption[] = [
  { label: "Apartment", patch: { property_type: "apartment" } },
  { label: "House", patch: { property_type: "house" } },
  { label: "Villa", patch: { property_type: "villa" } },
  { label: "Private room", patch: { property_type: "room" } },
  { label: "Cabin", patch: { property_type: "cabin" } },
];

const CAPACITY_OPTIONS: PatchOption[] = [
  { label: "2 guests / 1 room", patch: { max_guests: 2, number_of_rooms: 1 } },
  { label: "4 guests / 2 rooms", patch: { max_guests: 4, number_of_rooms: 2 } },
  { label: "6 guests / 3 rooms", patch: { max_guests: 6, number_of_rooms: 3 } },
  { label: "8 guests / 4 rooms", patch: { max_guests: 8, number_of_rooms: 4 } },
];

const FACT_OPTIONS: Record<string, { title: string; field: keyof AccommodationPatch; options: string[] }> = {
  amenities: {
    title: "Do you have any of these amenities?",
    field: "amenities",
    options: [
      "wifi",
      "air_conditioning",
      "parking",
      "kitchen",
      "balcony",
      "washing_machine",
      "dishwasher",
      "sea_view",
      "pool",
      "pet_friendly",
    ],
  },
  services: {
    title: "Do you offer or arrange any of these services?",
    field: "services_offered",
    options: [
      "self_check_in_support",
      "local_recommendations",
      "airport_transfer",
      "cleaning_service",
      "breakfast_arrangement",
      "bike_storage",
      "guided_tours",
    ],
  },
  specialties: {
    title: "Which local strengths should guests know about?",
    field: "expertise_areas",
    options: ["Gastronomy", "Local History", "Nature Activities", "Beaches", "Wine Tourism", "Family Activities"],
  },
  languages: {
    title: "Which guest languages can you support?",
    field: "languages",
    options: ["Croatian", "English", "German", "Italian", "French", "Spanish"],
  },
};

const COMPOSER_PLACEHOLDER: Record<string, string> = {
  property_name: "Property name...",
  location_core: "City and address...",
  gps: "Coordinates or confirm pin below",
  location_story: "Property story...",
  welcome_message: "Welcome message...",
  gallery: "Add photos below",
  rules: "Check-in, rules, pets...",
  amenities: "Add amenities...",
  services: "Add services...",
  specialties: "Add specialties...",
  languages: "Languages...",
};

function patchOptionIsSelected(pendingPatch: AccommodationPatch | null, option: PatchOption) {
  return Object.entries(option.patch).every(([key, value]) => pendingPatch?.[key as keyof AccommodationPatch] === value);
}

function patchOptionMatchesSnapshot(snapshot: AccommodationSnapshot, option: PatchOption) {
  return Object.entries(option.patch).every(([key, value]) => snapshot[key as keyof AccommodationPatch] === value);
}

function hasKnownLocation(snapshot: AccommodationSnapshot) {
  return Boolean(snapshot.city?.trim() && snapshot.address?.trim());
}

function propertyTypeLabel(value: string | undefined) {
  return PROPERTY_TYPE_OPTIONS.find((option) => option.patch.property_type === value)?.label || value || "";
}

export function AccommodationAiAgentPanel({
  snapshot,
  voiceEnabled,
  onApplyPatch,
  onEnhanceAll,
  onEditMissing,
}: AccommodationAiAgentPanelProps) {
  const agent = useAccommodationAgent(snapshot);
  const preview = agent.pendingPatch ? patchPreview(agent.pendingPatch) : [];
  const factOptions = agent.activeItemId ? FACT_OPTIONS[agent.activeItemId] : undefined;
  const selectedFactOptions =
    factOptions && Array.isArray(agent.pendingPatch?.[factOptions.field])
      ? (agent.pendingPatch[factOptions.field] as string[])
      : [];
  const patchOptions =
    agent.activeItemId === "property_type"
      ? {
          title: snapshot.property_type
            ? `Current type: ${propertyTypeLabel(snapshot.property_type)}. Confirm or choose another.`
            : "Choose the closest property type.",
          options: PROPERTY_TYPE_OPTIONS,
        }
      : agent.activeItemId === "capacity"
        ? {
            title:
              Number(snapshot.max_guests || 0) > 0 && Number(snapshot.number_of_rooms || 0) > 0
                ? `Current capacity: ${snapshot.max_guests} guests / ${snapshot.number_of_rooms} rooms. Confirm or choose another.`
                : "Choose a quick capacity preset, or type exact numbers.",
            options: CAPACITY_OPTIONS,
          }
        : null;
  const hasCurrentGps =
    typeof snapshot.latitude === "number" &&
    Number.isFinite(snapshot.latitude) &&
    typeof snapshot.longitude === "number" &&
    Number.isFinite(snapshot.longitude);
  const knownLocation = hasKnownLocation(snapshot);
  const knownPropertyName = Boolean(snapshot.property_name?.trim());
  const showGpsControl = agent.activeItemId === "gps";
  const showOpenFieldsControl =
    (agent.activeItemId === "property_name" && !knownPropertyName) ||
    (agent.activeItemId === "location_core" && !knownLocation) ||
    agent.activeItemId === "location_story" ||
    agent.activeItemId === "welcome_message" ||
    agent.activeItemId === "gallery" ||
    agent.activeItemId === "rules";
  const composerPlaceholder =
    (agent.activeItemId && COMPOSER_PLACEHOLDER[agent.activeItemId]) ||
    "Type here...";
  React.useEffect(() => {
    if (!agent.requestedEditItemId) return;
    onEditMissing?.(agent.requestedEditItemId);
    agent.consumeRequestedEdit();
  }, [agent, onEditMissing]);

  const handleComposerSend = (content: string) => {
    agent.sendMessage(
      content,
      factOptions
        ? {
            option_field: factOptions.field,
            visible_options: factOptions.options,
            selected_options: selectedFactOptions,
            interpretation_goal:
              "Use the visible options and pending draft to interpret conversational answers and corrections. For example, 'all of them' means every visible option; 'actually no pool' means remove pool from the current draft.",
          }
        : undefined,
    );
  };

  return (
    <div className="grid w-full min-w-0 max-w-full items-start gap-2 rounded-2xl border border-blue-100 bg-white/95 p-2.5 shadow-lg shadow-slate-950/5 backdrop-blur sm:gap-4 sm:p-4 lg:sticky lg:top-3 lg:z-30 lg:grid-cols-[280px_minmax(0,1fr)]">
      <AgentChecklist
        items={agent.checklist}
        activeId={agent.activeItemId}
        onSelect={agent.setActiveItemId}
        onEditMissing={onEditMissing}
        onReviewFacts={onEnhanceAll}
        compact
      />
      <div className="min-w-0 rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 via-white to-purple-50 p-2.5 sm:p-3">
        <div className="mb-2 flex items-start justify-between gap-2 sm:mb-4">
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-blue-700 sm:gap-2 sm:text-xs sm:tracking-[0.18em]">
              <Sparkles className="h-4 w-4" />
              AI Accommodation Assist
            </p>
            <h3 className="mt-0.5 truncate text-sm font-semibold text-gray-950 sm:mt-1 sm:text-lg">
              Build a better property profile
            </h3>
          </div>
          <details className="relative shrink-0">
            <summary
              className="flex h-8 w-8 cursor-pointer list-none items-center justify-center rounded-full border border-blue-200 bg-white text-blue-700 transition hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400 [&::-webkit-details-marker]:hidden"
              aria-label="How AI assist works"
              title="How AI assist works"
            >
              <Info className="h-4 w-4" />
            </summary>
            <div className="absolute right-0 z-20 mt-2 w-72 rounded-2xl border border-blue-100 bg-white p-3 text-xs leading-5 text-blue-950 shadow-xl">
              AI can organize and rewrite confirmed facts. Talk captures your words into the same
              Apply draft as typing — it does not save until you confirm. It cannot invent amenities
              you have not stated.
            </div>
          </details>
        </div>

        <div className="min-w-0 space-y-2 sm:space-y-4">
          <AgentMessageList messages={agent.messages} />
          {factOptions ? (
            <div className="min-w-0 space-y-2">
              <p className="text-sm font-medium text-blue-950">{factOptions.title}</p>
              <HorizontalChipScroller>
                {factOptions.options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => {
                      agent.togglePendingPatchOption(factOptions.field, option);
                    }}
                    aria-pressed={selectedFactOptions.includes(option)}
                    className={
                      selectedFactOptions.includes(option)
                        ? "shrink-0 rounded-full border border-blue-700 bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                        : "shrink-0 rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-medium text-blue-800 transition hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
                    }
                  >
                    {selectedFactOptions.includes(option) ? "✓ " : ""}
                    {option.replace(/_/g, " ")}
                  </button>
                ))}
              </HorizontalChipScroller>
            </div>
          ) : null}
          {patchOptions ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-blue-950">{patchOptions.title}</p>
              <div className="flex flex-wrap gap-2">
                {patchOptions.options.map((option) => {
                  const selected =
                    patchOptionIsSelected(agent.pendingPatch, option) ||
                    (!agent.pendingPatch && patchOptionMatchesSnapshot(snapshot, option));
                  return (
                    <button
                      key={option.label}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => agent.setPendingPatch(option.patch)}
                      className={
                        selected
                          ? "rounded-full border border-blue-700 bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                          : "rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-medium text-blue-800 transition hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
                      }
                    >
                      {selected ? "✓ " : ""}
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
          {showGpsControl ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-blue-950">Confirm the map pin used for local distances.</p>
              <div className="flex flex-wrap gap-2">
                {hasCurrentGps ? (
                  <button
                    type="button"
                    onClick={() => agent.setPendingPatch({ latitude: snapshot.latitude, longitude: snapshot.longitude })}
                    className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-medium text-blue-800 transition hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  >
                    Use current coordinates
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => onEditMissing?.("gps")}
                  className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 transition hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-300"
                >
                  Open coordinate fields
                </button>
              </div>
            </div>
          ) : null}
          {agent.activeItemId === "property_name" && knownPropertyName ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-blue-950">Check the saved public name before continuing.</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => agent.setPendingPatch({ property_name: snapshot.property_name })}
                  className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-medium text-blue-800 transition hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  Name is correct
                </button>
                <button
                  type="button"
                  onClick={() => onEditMissing?.("property_name")}
                  className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 transition hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-300"
                >
                  Edit name
                </button>
              </div>
            </div>
          ) : null}
          {agent.activeItemId === "location_core" && knownLocation ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-blue-950">Check the saved location before continuing.</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() =>
                    agent.setPendingPatch({
                      city: snapshot.city,
                      county: snapshot.county,
                      address: snapshot.address,
                    })
                  }
                  className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-medium text-blue-800 transition hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  Location is correct
                </button>
                <button
                  type="button"
                  onClick={() => onEditMissing?.("location_core")}
                  className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 transition hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-300"
                >
                  Edit location
                </button>
              </div>
            </div>
          ) : null}
          {showOpenFieldsControl ? (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => agent.activeItemId && onEditMissing?.(agent.activeItemId)}
                className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-medium text-blue-800 transition hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                Open matching fields
              </button>
            </div>
          ) : null}
          {agent.error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {agent.error}
            </div>
          )}
          <AgentComposer
            disabled={agent.isThinking}
            quickReplies={agent.pendingPatch ? [] : agent.quickReplies}
            voiceEnabled={voiceEnabled}
            voiceContext={{
              accommodation_snapshot: snapshot as Record<string, unknown>,
              checklist_state: agent.checklist,
              focused_item_id: agent.activeItemId,
              conversation_history: agent.messages.slice(-8),
              pending_patch: agent.pendingPatch,
            }}
            placeholder={agent.pendingPatch ? "Fix draft..." : composerPlaceholder}
            onSend={handleComposerSend}
            onVoiceIngested={(data, transcript) => {
              agent.applyAgentTurn(data, { userMessage: transcript });
            }}
          />
          {preview.length > 0 && agent.pendingPatch ? (
            <div className="rounded-2xl border-2 border-emerald-500 bg-emerald-50 p-3 shadow-lg shadow-emerald-950/10">
              <div className="mb-2 flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700">
                    Ready to apply
                  </p>
                  <h4 className="text-sm font-semibold text-emerald-950">Extracted facts to review</h4>
                </div>
                <Button
                  type="button"
                  size="sm"
                  className="shrink-0 bg-emerald-700 text-white hover:bg-emerald-800"
                  onClick={() => {
                    onApplyPatch(agent.pendingPatch!, { replaceFields: agent.pendingReplaceFields });
                    agent.markPatchApplied();
                  }}
                >
                  Apply
                </Button>
              </div>
              <div className="space-y-2 text-sm">
                {preview.map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-emerald-200 bg-white px-3 py-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">{key.replace(/_/g, " ")}</p>
                    <p className="mt-1 font-medium text-gray-900">
                      {Array.isArray(value) ? value.join(", ").replace(/_/g, " ") : String(value)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          <div className="flex justify-between gap-3 text-xs text-gray-500">
            <button type="button" className="underline" onClick={agent.skipActiveItem}>
              Skip
            </button>
            <span className="truncate">{agent.isThinking ? "Assistant is thinking..." : "Drafts save only after you tap Save."}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

