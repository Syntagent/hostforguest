"use client";

import Link from "next/link";
import React from "react";
import { Users } from "lucide-react";
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
  const hasGroups = guestGroups.length > 0;

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold text-gray-900 sm:text-2xl">Guest Groups</h2>
        <Button gradient onClick={onCreateGroup} className="w-full sm:w-auto">
          Create New Group
        </Button>
      </div>

      {!hasGroups ? (
        <div className="rounded-2xl border border-dashed border-blue-200 bg-blue-50/50 p-6 text-center sm:p-8">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-700">
            <Users className="h-6 w-6" aria-hidden />
          </div>
          <h3 className="text-lg font-semibold text-gray-900">No guest groups yet</h3>
          <p className="mx-auto mt-2 max-w-md text-sm text-gray-600">
            Create a group to get an access code. Guests use it to join and share preferences for
            your property guide.
          </p>
          <Button gradient onClick={onCreateGroup} className="mt-4 w-full sm:w-auto">
            Create New Group
          </Button>
          <p className="mt-3 text-xs text-gray-500">
            Groups link to your{" "}
            <Link href="/dashboard?tab=accommodation" className="font-medium text-blue-700 underline">
              Accommodation
            </Link>{" "}
            profile when saved.
          </p>
        </div>
      ) : (
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
                group.status === "completed" && "border-gray-200 bg-gray-50",
              ),
              content: (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-1 text-xs font-medium",
                        group.status === "active" && "bg-green-100 text-green-700",
                        group.status === "pending" && "bg-yellow-100 text-yellow-700",
                        group.status === "completed" && "bg-gray-100 text-gray-700",
                      )}
                    >
                      {group.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    Created: {new Date(group.created_at).toLocaleDateString()}
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full sm:w-auto"
                      onClick={() => onViewGroup(group)}
                    >
                      View Details
                    </Button>
                    {!group.access_code ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        className="w-full sm:w-auto"
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
                      className="w-full sm:w-auto"
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
          className="grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
        />
      )}
    </div>
  );
};
