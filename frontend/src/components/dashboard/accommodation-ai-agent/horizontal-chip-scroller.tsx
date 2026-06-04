"use client";

import { cn } from "@/lib/utils";

type HorizontalChipScrollerProps = {
  children: React.ReactNode;
  className?: string;
};

/** Mobile: swipe through chips. Desktop: wrap normally. */
export function HorizontalChipScroller({ children, className }: HorizontalChipScrollerProps) {
  return (
    <div
      className={cn(
        "w-full min-w-0 max-w-full overflow-x-auto overscroll-x-contain touch-pan-x pb-1 [-webkit-overflow-scrolling:touch] [scrollbar-width:none] sm:overflow-visible sm:pb-0 [&::-webkit-scrollbar]:hidden",
        className,
      )}
    >
      <div className="flex w-max gap-2 sm:w-auto sm:flex-wrap">{children}</div>
    </div>
  );
}
