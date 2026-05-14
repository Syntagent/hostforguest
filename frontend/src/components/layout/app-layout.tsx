"use client";

import React from "react";
import { Compass, PanelLeftClose, PanelLeftOpen } from "lucide-react";
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
            sidebarCollapsed ? "md:w-20" : "md:w-72"
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

          <div className="surface-glass flex h-full flex-col p-3">
            <div
              className={cn(
                "mb-4 rounded-2xl bg-gradient-to-br from-cyan-700 via-sky-700 to-orange-500 text-white",
                sidebarCollapsed
                  ? "flex items-center justify-center px-0 py-3"
                  : "px-4 py-4"
              )}
            >
              {sidebarCollapsed ? (
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20">
                  <Compass className="h-5 w-5" />
                </div>
              ) : (
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-white/80">
                    TouristGuideLocal
                  </p>
                  <p className="mt-1 text-sm font-semibold leading-tight">Host & Guest Experience</p>
                </div>
              )}
            </div>

            <nav className="space-y-1.5">
              {navItems.map((item) => {
                const isActive = item.id === activeItem;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onSelectItem(item.id)}
                    className={cn(
                      "flex w-full items-center rounded-2xl px-4 py-3 text-left text-sm font-medium transition-all",
                      sidebarCollapsed ? "justify-center" : "gap-3",
                      isActive
                        ? "bg-primary text-primary-foreground shadow"
                        : "text-foreground/80 hover:bg-primary/10 hover:text-foreground"
                    )}
                  >
                    <span className="text-base [&>svg]:h-4 [&>svg]:w-4" aria-hidden>
                      {item.icon}
                    </span>
                    {!sidebarCollapsed && <span>{item.label}</span>}
                  </button>
                );
              })}
            </nav>
          </div>
        </aside>

        <main className="min-w-0 flex-1 pb-24 md:pb-8">
          {(title || subtitle || headerActions) && (
            <header className="section-shell mb-4 mt-2 flex flex-col gap-3 px-4 py-3 sm:px-5 md:flex-row md:items-center md:justify-between">
              <div>
                {title && <h1 className="text-xl font-semibold text-foreground md:text-2xl">{title}</h1>}
                {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
              </div>
              {headerActions && <div className="flex flex-wrap items-center gap-2">{headerActions}</div>}
            </header>
          )}
          {children}
        </main>
      </div>

      <nav className="surface-glass fixed inset-x-3 bottom-3 z-50 flex items-center justify-between gap-1 p-1.5 md:hidden">
        {navItems.map((item) => {
          const isActive = item.id === activeItem;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectItem(item.id)}
              className={cn(
                "flex min-w-0 flex-1 flex-col items-center rounded-xl px-2 py-2.5 text-[11px] font-medium transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "text-foreground/70 hover:bg-primary/10"
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <span className="text-base leading-none [&>svg]:h-4 [&>svg]:w-4" aria-hidden>
                {item.icon}
              </span>
              <span className="mt-1 truncate">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
