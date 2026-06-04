import type { DashboardTab } from "@/components/dashboard/dashboard-tabs";

export type ComplianceItemStatus = "missing" | "done" | "skipped" | "not_applicable";
export type ComplianceRelevance = "required" | "optional" | "not_applicable";

export type ComplianceOfficialLink = {
  title: string;
  url: string;
};

export type ComplianceMergedItem = {
  id: string;
  label_hr: string;
  summary_hr: string;
  detail_hr?: string | null;
  applies_when: string[];
  deep_link?: string | null;
  official_links: ComplianceOfficialLink[];
  related_item_ids?: string[];
  status: ComplianceItemStatus;
  notes?: string | null;
  relevance: ComplianceRelevance;
};

export type ComplianceMergedCategory = {
  id: string;
  label_hr: string;
  items: ComplianceMergedItem[];
};

export type CompliancePdvRule = {
  id: string;
  title_hr: string;
  body_hr: string;
};

export type ComplianceHints = {
  suggest_uses_ota: boolean;
  has_evisitor_records: boolean;
};

export type ComplianceProgress = {
  total_relevant: number;
  done: number;
  percent: number;
};

export type ComplianceMe = {
  catalog_version: string;
  scenarios: Record<string, boolean>;
  categories: ComplianceMergedCategory[];
  pdv_regime_rules: CompliancePdvRule[];
  novasol_regime_rules: CompliancePdvRule[];
  progress: ComplianceProgress;
  hints: ComplianceHints;
};

export type ComplianceScenarioDef = {
  id: string;
  label_hr: string;
};

export type ComplianceCatalog = {
  version: string;
  last_reviewed: string;
  scenarios: ComplianceScenarioDef[];
  categories: Array<{
    id: string;
    label_hr: string;
    items: Array<{
      id: string;
      label_hr: string;
      summary_hr: string;
    }>;
  }>;
  pdv_regime_rules: CompliancePdvRule[];
  novasol_regime_rules: CompliancePdvRule[];
};

export type DeepLinkTarget = {
  tab: DashboardTab;
  query?: string;
};

export function resolveComplianceDeepLink(deepLink: string | null | undefined): DeepLinkTarget | null {
  if (!deepLink) return null;
  switch (deepLink) {
    case "guests_evisitor":
      return { tab: "groups", query: "open=evisitor" };
    case "channels":
      return { tab: "channels" };
    case "accommodation":
      return { tab: "accommodation" };
    default:
      return null;
  }
}

export const STATUS_LABELS: Record<ComplianceItemStatus, string> = {
  missing: "Na čekanju",
  done: "Obavljeno",
  skipped: "Preskočeno",
  not_applicable: "Ne primjenjuje se",
};
