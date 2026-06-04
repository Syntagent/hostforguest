"use client";

import Link from "next/link";
import React, { useMemo } from "react";
import { CalendarDays, MapPin, Users } from "lucide-react";
import { BentoGrid } from "@/components/ui/bento-grid";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { GuestGroup } from "@/lib/api";
import {
  formatStayDate,
  formatStayNightCount,
  getStayPhase,
  groupPropertyLabel,
  sortGuestGroupsByStay,
  stayPhaseLabel,
} from "./guest-group-stay";

export const GuestGroupsTab: React.FC<{
  guestGroups: GuestGroup[];
  onCreateGroup: () => void;
  onViewGroup: (group: GuestGroup) => void;
  onCopyAccessCode: (accessCode: string) => void;
  onRegenerateAccessCode: (groupId: string) => void;
  onDeleteGroup: (group: GuestGroup) => void;
  deletingGroupId: string | null;
  regeneratingGroupId: string | null;
}> = ({
  guestGroups,
  onCreateGroup,
  onViewGroup,
  onCopyAccessCode,
  onRegenerateAccessCode,
  onDeleteGroup,
  deletingGroupId,
  regeneratingGroupId,
}) => {
  const hasGroups = guestGroups.length > 0;
  const sortedGroups = useMemo(() => sortGuestGroupsByStay(guestGroups), [guestGroups]);
  const undatedCount = guestGroups.filter((g) => !g.check_in_date || !g.check_out_date).length;

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 sm:text-2xl">Guest Groups</h2>
          {hasGroups ? (
            <p className="mt-1 text-sm text-gray-600">
              Sorted by arrival date — like a stay calendar at your property.
            </p>
          ) : null}
        </div>
        <Button gradient onClick={onCreateGroup} className="w-full sm:w-auto">
          Create New Group
        </Button>
      </div>

      {undatedCount > 0 && hasGroups ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          {undatedCount} group{undatedCount === 1 ? "" : "s"} missing arrival or departure dates.
          Open <strong>View Details</strong> to add stay dates for better recommendations.
        </div>
      ) : null}

      {!hasGroups ? (
        <div className="rounded-2xl border border-dashed border-blue-200 bg-blue-50/50 p-6 text-center sm:p-8">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-700">
            <Users className="h-6 w-6" aria-hidden />
          </div>
          <h3 className="text-lg font-semibold text-gray-900">No guest groups yet</h3>
          <p className="mx-auto mt-2 max-w-md text-sm text-gray-600">
            Create a group with arrival and departure dates. Guests use the access code to join and
            get recommendations timed to their stay.
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
          items={sortedGroups.map((group) => {
            const propLine = groupPropertyLabel(group);
            const phase = getStayPhase(group);
            const hasStay = Boolean(group.check_in_date && group.check_out_date);
            const nights =
              hasStay && group.check_in_date && group.check_out_date
                ? formatStayNightCount(group.check_in_date, group.check_out_date)
                : null;

            return {
              title: group.group_name,
              description: [
                hasStay
                  ? `${formatStayDate(group.check_in_date)} → ${formatStayDate(group.check_out_date)}`
                  : "Stay dates not set",
                propLine ? propLine : null,
                `${group.group_size} guests`,
              ]
                .filter(Boolean)
                .join(" • "),
              icon: "👥",
              className: cn(
                phase === "in_house" && "border-green-300 bg-green-50/80",
                phase === "upcoming" && "border-blue-200 bg-blue-50/80",
                phase === "completed" && "border-gray-200 bg-gray-50",
                phase === "unknown" && "border-amber-200 bg-amber-50/60"
              ),
              content: (
                <div className="space-y-3">
                  <div
                    className={cn(
                      "rounded-lg border p-3",
                      phase === "in_house" && "border-green-200 bg-white",
                      phase === "upcoming" && "border-blue-200 bg-white",
                      phase === "completed" && "border-gray-200 bg-white",
                      phase === "unknown" && "border-amber-200 bg-white"
                    )}
                  >
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium text-gray-600">
                      <CalendarDays className="h-3.5 w-3.5 shrink-0" aria-hidden />
                      Stay schedule
                    </div>
                    {hasStay ? (
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="block text-xs text-gray-500">Arrives</span>
                          <span className="font-medium text-gray-900">
                            {formatStayDate(group.check_in_date)}
                          </span>
                        </div>
                        <div>
                          <span className="block text-xs text-gray-500">Leaves</span>
                          <span className="font-medium text-gray-900">
                            {formatStayDate(group.check_out_date)}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-amber-900">Add arrival & departure in group details</p>
                    )}
                    {propLine ? (
                      <p className="mt-2 flex items-start gap-1.5 text-xs text-gray-600">
                        <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                        <span>{propLine}</span>
                      </p>
                    ) : null}
                    {nights != null ? (
                      <p className="mt-2 text-xs text-gray-500">
                        {nights} night{nights === 1 ? "" : "s"}
                      </p>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-1 text-xs font-medium",
                        phase === "in_house" && "bg-green-100 text-green-800",
                        phase === "upcoming" && "bg-blue-100 text-blue-800",
                        phase === "completed" && "bg-gray-100 text-gray-700",
                        phase === "unknown" && "bg-amber-100 text-amber-900"
                      )}
                    >
                      {stayPhaseLabel(phase)}
                    </span>
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
                    Code:{" "}
                    <span className="font-mono text-gray-800">{group.access_code ?? "—"}</span>
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
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full border-red-200 text-red-700 hover:bg-red-50 sm:w-auto"
                      disabled={String(deletingGroupId) === String(group.id)}
                      onClick={() => onDeleteGroup(group)}
                    >
                      {String(deletingGroupId) === String(group.id) ? "Deleting…" : "Delete"}
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
