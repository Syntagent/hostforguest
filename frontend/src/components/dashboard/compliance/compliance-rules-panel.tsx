"use client";

import { cn } from "@/lib/utils";
import type { CompliancePdvRule } from "./compliance-catalog";

type Variant = "blue" | "emerald";

const VARIANT_STYLES: Record<
  Variant,
  { wrap: string; title: string; subtitle: string; itemBorder: string }
> = {
  blue: {
    wrap: "border-blue-200 bg-blue-50/50",
    title: "text-blue-950",
    subtitle: "text-blue-900/80",
    itemBorder: "border-blue-100",
  },
  emerald: {
    wrap: "border-emerald-200 bg-emerald-50/50",
    title: "text-emerald-950",
    subtitle: "text-emerald-900/80",
    itemBorder: "border-emerald-100",
  },
};

type Props = {
  rules: CompliancePdvRule[];
  title: string;
  subtitle: string;
  variant?: Variant;
  forceVisible?: boolean;
};

export function ComplianceRulesPanel({
  rules,
  title,
  subtitle,
  variant = "blue",
  forceVisible,
}: Props) {
  if (!forceVisible && rules.length === 0) {
    return null;
  }

  const styles = VARIANT_STYLES[variant];

  return (
    <div
      className={cn(
        "w-full rounded-3xl border p-4 shadow-sm sm:p-5",
        styles.wrap
      )}
    >
      <h3 className={cn("text-sm font-semibold", styles.title)}>{title}</h3>
      <p className={cn("mt-1 text-xs", styles.subtitle)}>{subtitle}</p>
      <ul className="mt-3 space-y-3">
        {rules.map((rule) => (
          <li
            key={rule.id}
            className={cn("rounded-lg border bg-white p-3", styles.itemBorder)}
          >
            <p className="text-sm font-medium text-gray-900">{rule.title_hr}</p>
            <p className="mt-1 text-sm text-muted-foreground">{rule.body_hr}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
