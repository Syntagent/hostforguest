"use client";

import { Check, Circle, ExternalLink, MinusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type {
  ComplianceMergedCategory,
  ComplianceMergedItem,
  ComplianceItemStatus,
} from "./compliance-catalog";
import { STATUS_LABELS } from "./compliance-catalog";

const statusIcon = {
  done: Check,
  skipped: MinusCircle,
  missing: Circle,
  not_applicable: MinusCircle,
};

type Props = {
  categories: ComplianceMergedCategory[];
  busy?: boolean;
  onStatusChange: (itemId: string, status: ComplianceItemStatus) => void;
  onDeepLink?: (item: ComplianceMergedItem) => void;
  onAskAbout?: (item: ComplianceMergedItem) => void;
};

export function ComplianceChecklist({
  categories,
  busy,
  onStatusChange,
  onDeepLink,
  onAskAbout,
}: Props) {
  return (
    <div className="w-full space-y-3">
      {categories.map((cat) => (
        <details
          key={cat.id}
          className="group w-full rounded-3xl border border-border bg-card shadow-sm"
          open
        >
          <summary className="cursor-pointer list-none px-4 py-3 font-semibold text-gray-900 marker:content-none">
            <span className="flex items-center justify-between gap-2">
              {cat.label_hr}
              <span className="text-xs font-normal text-muted-foreground">
                {cat.items.filter((i) => i.relevance !== "not_applicable").length} stavki
              </span>
            </span>
          </summary>
          <ul className="divide-y border-t border-border px-2 pb-2">
            {cat.items.map((item) => (
              <ComplianceChecklistRow
                key={item.id}
                item={item}
                busy={busy}
                onStatusChange={onStatusChange}
                onDeepLink={onDeepLink}
                onAskAbout={onAskAbout}
              />
            ))}
          </ul>
        </details>
      ))}
    </div>
  );
}

function ComplianceChecklistRow({
  item,
  busy,
  onStatusChange,
  onDeepLink,
  onAskAbout,
}: {
  item: ComplianceMergedItem;
  busy?: boolean;
  onStatusChange: (itemId: string, status: ComplianceItemStatus) => void;
  onDeepLink?: (item: ComplianceMergedItem) => void;
  onAskAbout?: (item: ComplianceMergedItem) => void;
}) {
  const Icon = statusIcon[item.status] ?? Circle;
  const muted = item.relevance === "not_applicable";

  return (
    <li className={cn("px-2 py-3", muted && "opacity-60")}>
      <div className="flex gap-3">
        <Icon
          className={cn(
            "mt-0.5 h-5 w-5 shrink-0",
            item.status === "done" && "text-green-600",
            item.status === "missing" && "text-gray-400",
            item.status === "skipped" && "text-amber-600",
            item.status === "not_applicable" && "text-gray-300"
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="font-medium text-gray-900">{item.label_hr}</p>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              {STATUS_LABELS[item.status]}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{item.summary_hr}</p>
          {item.official_links.length > 0 ? (
            <ul className="mt-2 space-y-1">
              {item.official_links.map((link) => (
                <li key={link.url}>
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
                  >
                    {link.title}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </li>
              ))}
            </ul>
          ) : null}
          <div className="mt-2 flex flex-wrap gap-2">
            {item.status !== "done" && item.relevance !== "not_applicable" ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={busy}
                className="h-7 text-xs"
                onClick={() => onStatusChange(item.id, "done")}
              >
                Označi obavljeno
              </Button>
            ) : null}
            {item.status === "done" ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={busy}
                className="h-7 text-xs"
                onClick={() => onStatusChange(item.id, "missing")}
              >
                Poništi
              </Button>
            ) : null}
            {item.relevance !== "not_applicable" && item.status !== "skipped" ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={busy}
                className="h-7 text-xs"
                onClick={() => onStatusChange(item.id, "skipped")}
              >
                Preskoči
              </Button>
            ) : null}
            {item.deep_link && item.deep_link !== "external" && onDeepLink ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="h-7 text-xs"
                onClick={() => onDeepLink(item)}
              >
                Otvori u aplikaciji
              </Button>
            ) : null}
            {onAskAbout ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-7 text-xs"
                onClick={() => onAskAbout(item)}
              >
                Pitaj AI
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </li>
  );
}
