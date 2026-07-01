"use client";

import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AccommodationPatch } from "@/lib/api";
import { ACCOMMODATION_CHECKLIST, type AccommodationSnapshot } from "./accommodation-checklist";
import { AgentChecklist } from "./agent-checklist";
import { AgentComposer } from "./agent-composer";
import { AgentMessageList } from "./agent-message-list";
import { useAccommodationAgent } from "./use-accommodation-agent";

type AccommodationAiAgentPanelProps = {
  snapshot: AccommodationSnapshot;
  voiceEnabled?: boolean;
  onApplyPatch: (patch: AccommodationPatch) => void;
  onEnhanceAll: () => void;
  isEnhancingAll?: boolean;
};

function patchPreview(patch: AccommodationPatch) {
  return Object.entries(patch).filter(([, value]) => {
    if (Array.isArray(value)) return value.length > 0;
    return value !== undefined && value !== null && value !== "";
  });
}

export function AccommodationAiAgentPanel({
  snapshot,
  voiceEnabled,
  onApplyPatch,
  onEnhanceAll,
  isEnhancingAll,
}: AccommodationAiAgentPanelProps) {
  const agent = useAccommodationAgent(snapshot);
  const activePrompt = ACCOMMODATION_CHECKLIST.find((item) => item.id === agent.activeItemId)?.prompt;
  const preview = agent.pendingPatch ? patchPreview(agent.pendingPatch) : [];

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <AgentChecklist items={agent.checklist} activeId={agent.activeItemId} onSelect={agent.setActiveItemId} />
      <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 via-white to-purple-50 p-4 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              <Sparkles className="h-4 w-4" />
              Stay assistant
            </p>
            <h3 className="mt-1 text-lg font-semibold text-gray-950">Turn host knowledge into guest-ready facts</h3>
            <p className="mt-1 text-sm text-gray-600">
              {activePrompt ?? "Answer one focused question, then review the suggested profile update."}
            </p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={onEnhanceAll} disabled={isEnhancingAll}>
            {isEnhancingAll ? "Enhancing..." : "Enhance all"}
          </Button>
        </div>

        <div className="space-y-4">
          <AgentMessageList messages={agent.messages} />
          {agent.error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {agent.error}
            </div>
          )}
          {preview.length > 0 && agent.pendingPatch && (
            <div className="rounded-2xl border border-green-200 bg-green-50 p-3">
              <div className="mb-2 flex items-center justify-between gap-3">
                <h4 className="text-sm font-semibold text-green-950">Draft suggestion</h4>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    onApplyPatch(agent.pendingPatch!);
                    agent.markPatchApplied();
                  }}
                >
                  Apply draft
                </Button>
              </div>
              <div className="space-y-2 text-sm">
                {preview.map(([key, value]) => (
                  <div key={key} className="rounded-xl bg-white px-3 py-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{key.replace(/_/g, " ")}</p>
                    <p className="mt-1 text-gray-800">
                      {Array.isArray(value) ? value.join(", ").replace(/_/g, " ") : String(value)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
          <AgentComposer
            disabled={agent.isThinking}
            quickReplies={agent.quickReplies}
            voiceEnabled={voiceEnabled}
            onSend={agent.sendMessage}
          />
          <div className="flex justify-between text-xs text-gray-500">
            <button type="button" className="underline" onClick={agent.skipActiveItem}>
              Skip this item
            </button>
            <span>{agent.isThinking ? "Assistant is thinking..." : "Suggestions are drafts until you save changes."}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

