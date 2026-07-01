"use client";

import { Check, Circle, Clock, MinusCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AccommodationChecklistItemState } from "@/lib/api";
import { checklistProgress } from "./accommodation-checklist";

type AgentChecklistProps = {
  items: AccommodationChecklistItemState[];
  activeId?: string | null;
  onSelect: (id: string) => void;
};

const statusIcon = {
  done: Check,
  draft: Clock,
  in_progress: Clock,
  skipped: MinusCircle,
  missing: Circle,
};

export function AgentChecklist({ items, activeId, onSelect }: AgentChecklistProps) {
  const progress = checklistProgress(items);

  return (
    <div className="rounded-2xl border border-border bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Promotion checklist</h3>
          <p className="text-xs text-gray-500">Facts the assistant will help collect.</p>
        </div>
        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
          {progress}%
        </span>
      </div>
      <div className="mb-3 h-2 overflow-hidden rounded-full bg-gray-100">
        <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
      </div>
      <div className="space-y-1.5">
        {items.map((item) => {
          const Icon = statusIcon[item.status] ?? Circle;
          const isActive = item.id === activeId;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
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
              <span className="text-[11px] capitalize text-gray-500">{item.status.replace("_", " ")}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

