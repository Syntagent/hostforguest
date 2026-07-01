"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  DEFAULT_DASHBOARD_TAB,
  type DashboardTab,
  buildDashboardTabHref,
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
    (tab: DashboardTab) => {
      setActiveTab(tab);
      const href = buildDashboardTabHref(pathname, tab, searchParams.toString());
      router.replace(href, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  return { activeTab, selectTab };
}
