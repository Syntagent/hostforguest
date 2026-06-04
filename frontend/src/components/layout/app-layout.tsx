"use client";

import React from "react";
import { Compass, MoreHorizontal, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface AppNavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

interface AppLayoutProps {
  title?: string;
  subtitle?: string;
  navItems: AppNavItem[];
  activeItem: string;
  onSelectItem: (id: string) => void;
  headerActions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  title,
  subtitle,
  navItems,
  activeItem,
  onSelectItem,
  headerActions,
  children,
  className,
}) => {
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  const [mobileMoreOpen, setMobileMoreOpen] = React.useState(false);
  const primaryMobileItems = navItems.slice(0, 4);
  const overflowMobileItems = navItems.slice(4);
  const isOverflowActive = overflowMobileItems.some((item) => item.id === activeItem);
  const selectMobileItem = (id: string) => {
    setMobileMoreOpen(false);
    onSelectItem(id);
  };

  React.useEffect(() => {
    const media = window.matchMedia("(max-width: 1280px)");
    const applyResponsiveDefault = () => setSidebarCollapsed(media.matches);
    applyResponsiveDefault();
    media.addEventListener("change", applyResponsiveDefault);
    return () => media.removeEventListener("change", applyResponsiveDefault);
  }, []);

  return (
    <div className={cn("min-h-screen", className)}>
      <div className="mx-auto flex max-w-[1600px] gap-0 md:gap-6 lg:gap-8 md:px-4 lg:px-6">
        <aside
          className={cn(
            "relative hidden md:sticky md:top-4 md:block md:h-[calc(100vh-2rem)] md:shrink-0 md:py-4",
            sidebarCollapsed ? "md:w-[4.25rem]" : "md:w-max"
          )}
        >
          <button
            type="button"
            onClick={() => setSidebarCollapsed((prev) => !prev)}
            className="absolute -right-4 top-1/2 z-20 hidden h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-card text-foreground/70 shadow-sm transition hover:bg-accent hover:text-accent-foreground lg:inline-flex"
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={sidebarCollapsed ? "Expand menu" : "Collapse menu"}
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>

          <div
            className={cn(
              "surface-glass flex h-full min-h-0 flex-col overflow-hidden",
              sidebarCollapsed ? "w-full p-2" : "w-max max-w-full p-2"
            )}
          >
            <div
              className={cn(
                "mb-2 shrink-0 rounded-xl bg-gradient-to-br from-cyan-700 via-sky-700 to-orange-500 text-white",
                sidebarCollapsed
                  ? "flex items-center justify-center px-0 py-2"
                  : "px-2 py-2"
              )}
            >
              {sidebarCollapsed ? (
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/20">
                  <Compass className="h-4 w-4" />
                </div>
              ) : (
                <div className="w-max">
                  <p className="text-[10px] uppercase tracking-[0.12em] text-white/80 whitespace-nowrap">
                    H4G
                  </p>
                </div>
              )}
            </div>

            <nav
              className={cn(
                "min-h-0 flex-1 space-y-0.5 overflow-y-auto overscroll-contain",
                !sidebarCollapsed && "w-max"
              )}
              role="tablist"
              aria-label="Dashboard sections"
            >
              {navItems.map((item) => {
                const isActive = item.id === activeItem;
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="tab"
                    aria-label={item.label}
                    aria-selected={isActive}
                    data-testid={`app-nav-${item.id}`}
                    onClick={() => onSelectItem(item.id)}
                    className={cn(
                      "flex items-center rounded-lg text-left text-[13px] font-medium transition-all",
                      sidebarCollapsed
                        ? "w-full justify-center px-2 py-2"
                        : "w-full gap-1.5 px-2 py-1.5",
                      isActive
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-foreground/80 hover:bg-primary/10 hover:text-foreground"
                    )}
                  >
                    <span className="shrink-0 [&>svg]:h-4 [&>svg]:w-4" aria-hidden>
                      {item.icon}
                    </span>
                    {!sidebarCollapsed && (
                      <span className="whitespace-nowrap leading-snug">{item.label}</span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        </aside>

        <main className="min-w-0 flex-1 pb-[calc(5.25rem+env(safe-area-inset-bottom))] md:pb-8">
          {(title || subtitle || headerActions) && (
            <header className="section-shell mb-2 mt-1 flex items-center justify-between gap-2 px-3 py-2 sm:mb-4 sm:mt-2 sm:px-5 sm:py-3">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-primary text-xs font-bold tracking-tight text-primary-foreground shadow-sm">
                  H4G
                </div>
                <div className="min-w-0">
                  {title && <h1 className="truncate text-sm font-semibold text-foreground sm:text-lg md:text-2xl">{title}</h1>}
                  {subtitle && <p className="hidden text-sm text-muted-foreground sm:block">{subtitle}</p>}
                </div>
              </div>
              {headerActions && <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">{headerActions}</div>}
            </header>
          )}
          {children}
        </main>
      </div>

      <nav
        className="surface-glass fixed inset-x-0 bottom-0 z-50 grid grid-cols-5 gap-0 rounded-none rounded-t-2xl border-b-0 border-t border-border/60 px-1 pt-1 pb-[max(0.25rem,env(safe-area-inset-bottom))] shadow-[0_-10px_30px_-18px_hsl(206_52%_22%_/_0.45)] md:hidden"
        role="tablist"
        aria-label="Dashboard sections"
      >
        {primaryMobileItems.map((item) => {
          const isActive = item.id === activeItem;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-label={item.label}
              aria-selected={isActive}
              data-testid={`app-nav-${item.id}`}
              onClick={() => selectMobileItem(item.id)}
              className={cn(
                "flex min-w-0 flex-col items-center rounded-xl px-1 py-2.5 text-[11px] font-medium transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "text-foreground/70 hover:bg-primary/10"
              )}
            >
              <span className="text-base leading-none [&>svg]:h-4 [&>svg]:w-4" aria-hidden>
                {item.icon}
              </span>
              <span className="mt-1 truncate">{item.label}</span>
            </button>
          );
        })}
        {overflowMobileItems.length > 0 && (
          <button
            type="button"
            role="tab"
            aria-label="More dashboard sections"
            aria-selected={isOverflowActive}
            onClick={() => setMobileMoreOpen(true)}
            className={cn(
              "flex min-w-0 flex-col items-center rounded-xl px-1 py-2.5 text-[11px] font-medium transition-colors",
              isOverflowActive ? "bg-primary text-primary-foreground" : "text-foreground/70 hover:bg-primary/10"
            )}
          >
            <span className="text-base leading-none" aria-hidden>
              <MoreHorizontal className="h-4 w-4" />
            </span>
            <span className="mt-1 truncate">More</span>
          </button>
        )}
      </nav>

      {mobileMoreOpen && (
        <div className="fixed inset-0 z-40 bg-black/35 p-3 md:hidden" onClick={() => setMobileMoreOpen(false)}>
          <div
            className="surface-glass absolute inset-x-3 bottom-[calc(4.75rem+env(safe-area-inset-bottom))] max-h-[60vh] overflow-y-auto rounded-3xl p-3 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-2 flex items-center justify-between px-1">
              <p className="text-sm font-semibold text-foreground">More sections</p>
              <button
                type="button"
                onClick={() => setMobileMoreOpen(false)}
                className="rounded-full p-2 text-muted-foreground transition hover:bg-primary/10 hover:text-foreground"
                aria-label="Close more sections"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {overflowMobileItems.map((item) => {
                const isActive = item.id === activeItem;
                return (
                  <button
                    key={item.id}
                    type="button"
                    data-testid={`app-nav-${item.id}`}
                    onClick={() => selectMobileItem(item.id)}
                    className={cn(
                      "flex items-center gap-2 rounded-2xl px-3 py-3 text-left text-sm font-medium transition",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "bg-background/70 text-foreground/80 hover:bg-primary/10"
                    )}
                  >
                    <span className="[&>svg]:h-4 [&>svg]:w-4" aria-hidden>
                      {item.icon}
                    </span>
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
