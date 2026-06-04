"use client";

import { Check, Circle, Clock, MinusCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AccommodationChecklistItemState } from "@/lib/api";
import { checklistProgress } from "./accommodation-checklist";
import { HorizontalChipScroller } from "./horizontal-chip-scroller";

type AgentChecklistProps = {
  items: AccommodationChecklistItemState[];
  activeId?: string | null;
  onSelect: (id: string) => void;
  onEditMissing?: (id: string) => void;
  onReviewFacts?: () => void;
  compact?: boolean;
};

const statusIcon = {
  done: Check,
  draft: Clock,
  in_progress: Clock,
  skipped: MinusCircle,
  missing: Circle,
};

export function AgentChecklist({ items, activeId, onSelect, onEditMissing, onReviewFacts, compact }: AgentChecklistProps) {
  const progress = checklistProgress(items);
  const missingItems = items.filter((item) => item.status === "missing");

  if (compact) {
    return (
      <div className="rounded-2xl border border-border bg-white p-2.5 shadow-sm sm:p-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <h3 className="min-w-0 text-sm font-semibold text-gray-900">Promotion checklist</h3>
          <div className="flex shrink-0 items-center gap-2">
            {onReviewFacts ? (
              <button
                type="button"
                onClick={onReviewFacts}
                className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                Review
              </button>
            ) : null}
            <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
              {progress}%
            </span>
          </div>
        </div>
        {missingItems.length > 0 ? (
          <HorizontalChipScroller>
            {missingItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  onSelect(item.id);
                  onEditMissing?.(item.id);
                }}
                className={cn(
                  "shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-amber-300",
                  item.id === activeId
                    ? "border-blue-600 bg-blue-50 text-blue-900"
                    : "border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100",
                )}
              >
                Fix {item.label ?? item.id}
              </button>
            ))}
          </HorizontalChipScroller>
        ) : (
          <p className="text-xs font-medium text-green-700">All key facts are complete.</p>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-white p-3 shadow-sm sm:p-4">
      <div className="mb-2 flex items-center justify-between gap-3 sm:mb-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900">Promotion checklist</h3>
          <p className="hidden text-xs text-gray-500 sm:block">Confirm real facts before guest-facing copy is generated.</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {onReviewFacts ? (
            <button
              type="button"
              onClick={onReviewFacts}
              className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              Review
            </button>
          ) : null}
          <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
            {progress}%
          </span>
        </div>
      </div>
      <div className="sm:hidden">
        {missingItems.length > 0 ? (
          <HorizontalChipScroller>
            {missingItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  onSelect(item.id);
                  onEditMissing?.(item.id);
                }}
                className={cn(
                  "shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-amber-300",
                  item.id === activeId
                    ? "border-blue-600 bg-blue-50 text-blue-900"
                    : "border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100",
                )}
              >
                Fix {item.label ?? item.id}
              </button>
            ))}
          </HorizontalChipScroller>
        ) : (
          <p className="text-xs font-medium text-green-700">All key facts are complete.</p>
        )}
      </div>
      <div className="hidden space-y-1.5 sm:block">
        {items.map((item) => {
          const Icon = statusIcon[item.status] ?? Circle;
          const isActive = item.id === activeId;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                onSelect(item.id);
                if (item.status === "missing") onEditMissing?.(item.id);
              }}
              className={cn(
                "flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-sm transition",
                isActive ? "bg-blue-50 text-blue-900" : "hover:bg-gray-50",
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  item.status === "done" && "text-green-600",
                  item.status === "draft" && "text-blue-600",
                  item.status === "missing" && "text-gray-400",
                )}
              />
              <span className="min-w-0 flex-1 truncate">{item.label ?? item.id}</span>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[11px] capitalize",
                  item.status === "missing" ? "bg-amber-50 text-amber-700" : "text-gray-500",
                )}
              >
                {item.status === "missing" ? "Fix" : item.status.replace("_", " ")}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

