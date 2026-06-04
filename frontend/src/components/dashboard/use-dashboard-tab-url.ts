"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  DEFAULT_DASHBOARD_TAB,
  type DashboardTab,
  dashboardTabQueryValue,
  parseDashboardTabParam,
} from "./dashboard-tabs";

function tabFromSearchParams(searchParams: URLSearchParams): DashboardTab {
  return parseDashboardTabParam(searchParams.get("tab")) ?? DEFAULT_DASHBOARD_TAB;
}

export function useDashboardTabUrl() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<DashboardTab>(() =>
    tabFromSearchParams(searchParams)
  );

  useEffect(() => {
    const fromUrl = tabFromSearchParams(searchParams);
    setActiveTab((current) => (current === fromUrl ? current : fromUrl));
  }, [searchParams]);

  const selectTab = useCallback(
    (tab: DashboardTab, extraQuery?: string) => {
      setActiveTab(tab);
      const params = new URLSearchParams(searchParams.toString());
      const q = dashboardTabQueryValue(tab);
      if (q) params.set("tab", q);
      else params.delete("tab");
      if (extraQuery) {
        for (const part of extraQuery.split("&")) {
          const [key, value] = part.split("=");
          if (key) params.set(key, value ?? "");
        }
      }
      const query = params.toString();
      const href = query ? `${pathname}?${query}` : pathname;
      router.replace(href, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  return { activeTab, selectTab };
}
