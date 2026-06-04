"use client";

import { cn } from "@/lib/utils";
import type { ComplianceHints, ComplianceScenarioDef } from "./compliance-catalog";

type Props = {
  scenarios: ComplianceScenarioDef[];
  active: Record<string, boolean>;
  hints: ComplianceHints;
  disabled?: boolean;
  onToggle: (id: string, value: boolean) => void;
};

export function ComplianceScenarios({
  scenarios,
  active,
  hints,
  disabled,
  onToggle,
}: Props) {
  return (
    <div className="w-full rounded-3xl border border-border bg-card p-4 shadow-sm sm:p-5">
      <h3 className="text-sm font-semibold text-gray-900">Vaša situacija</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Označite što vrijedi za vas — checklista će označiti relevantne obveze.
      </p>
      {(hints.suggest_uses_ota || hints.has_evisitor_records) && (
        <div className="mt-2 space-y-1 text-xs text-amber-800">
          {hints.suggest_uses_ota ? (
            <p>💡 Povezan Booking kanal — razmislite o scenariju OTA / PDV.</p>
          ) : null}
          {hints.has_evisitor_records ? (
            <p>💡 Imate zapise u eVisitoru — provjerite stavku prijave gostiju.</p>
          ) : null}
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {scenarios.map((s) => {
          const on = Boolean(active[s.id]);
          return (
            <button
              key={s.id}
              type="button"
              disabled={disabled}
              onClick={() => onToggle(s.id, !on)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400",
                on
                  ? "border-blue-600 bg-blue-600 text-white"
                  : "border-border bg-muted/30 text-gray-800 hover:bg-muted/60",
                disabled && "opacity-60"
              )}
            >
              {s.label_hr}
            </button>
          );
        })}
      </div>
    </div>
  );
}
