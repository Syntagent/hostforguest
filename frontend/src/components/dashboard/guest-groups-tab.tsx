"use client";

import React from "react";
import { BentoGrid } from "@/components/ui/bento-grid";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { GuestGroup } from "@/lib/api";

export const GuestGroupsTab: React.FC<{
  guestGroups: GuestGroup[];
  onCreateGroup: () => void;
  onViewGroup: (group: GuestGroup) => void;
  onCopyAccessCode: (accessCode: string) => void;
  onRegenerateAccessCode: (groupId: string) => void;
  regeneratingGroupId: string | null;
}> = ({
  guestGroups,
  onCreateGroup,
  onViewGroup,
  onCopyAccessCode,
  onRegenerateAccessCode,
  regeneratingGroupId,
}) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Guest Groups Management</h2>
        <Button gradient onClick={onCreateGroup}>
          Create New Group
        </Button>
      </div>

      <BentoGrid
        items={guestGroups.map((group) => {
          const propLine =
            group.accommodation?.property_name?.trim() ||
            [group.accommodation?.city, group.accommodation?.address?.split(",")[0]?.trim()]
              .filter(Boolean)
              .join(" · ") ||
            null;
          return {
          title: group.group_name,
          description: [
            propLine ? `Property: ${propLine}` : null,
            `${group.group_size} guests`,
            `Access code: ${group.access_code ?? "—"}`,
          ]
            .filter(Boolean)
            .join(" • "),
          icon: "👥",
          className: cn(
            group.status === "active" && "border-green-200 bg-green-50",
            group.status === "pending" && "border-yellow-200 bg-yellow-50",
            group.status === "completed" && "border-gray-200 bg-gray-50"
          ),
          content: (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "rounded-full px-2 py-1 text-xs font-medium",
                    group.status === "active" && "bg-green-100 text-green-700",
                    group.status === "pending" && "bg-yellow-100 text-yellow-700",
                    group.status === "completed" && "bg-gray-100 text-gray-700"
                  )}
                >
                  {group.status}
                </span>
              </div>
              <div className="text-sm text-gray-600">
                Created: {new Date(group.created_at).toLocaleDateString()}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => onViewGroup(group)}>
                  View Details
                </Button>
                {!group.access_code ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={String(regeneratingGroupId) === String(group.id)}
                    onClick={() => onRegenerateAccessCode(String(group.id))}
                  >
                    {String(regeneratingGroupId) === String(group.id)
                      ? "Generating…"
                      : "Generate access code"}
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!group.access_code}
                  title={
                    !group.access_code
                      ? "Generate an access code first, or open View Details"
                      : undefined
                  }
                  onClick={() => group.access_code && onCopyAccessCode(group.access_code)}
                >
                  Copy Access Code
                </Button>
              </div>
            </div>
          ),
        };
        })}
        className="grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
      />
    </div>
  );
};
