"use client";

import React from "react";
import { complianceApi } from "@/lib/api";
import type { ComplianceCatalog, ComplianceMe } from "./compliance-catalog";

export function useCompliance() {
  const [data, setData] = React.useState<ComplianceMe | null>(null);
  const [catalog, setCatalog] = React.useState<ComplianceCatalog | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const [meRes, catRes] = await Promise.all([
      complianceApi.getMe(),
      complianceApi.getCatalog(),
    ]);
    if (!meRes.success || !meRes.data) {
      setError(meRes.error || "Ne mogu učitati obveze.");
      setLoading(false);
      return;
    }
    setData(meRes.data);
    if (catRes.success && catRes.data) {
      setCatalog(catRes.data);
    }
    setLoading(false);
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const updateScenarios = React.useCallback(
    async (scenarios: Record<string, boolean>) => {
      setBusy(true);
      const res = await complianceApi.updateScenarios({ scenarios });
      setBusy(false);
      if (res.success && res.data) {
        setData(res.data);
      } else {
        setError(res.error || "Spremanje scenarija nije uspjelo.");
      }
    },
    []
  );

  const patchItem = React.useCallback(
    async (itemId: string, status: ComplianceMe["categories"][0]["items"][0]["status"], notes?: string) => {
      setBusy(true);
      const res = await complianceApi.patchItem(itemId, { status, notes });
      setBusy(false);
      if (res.success && res.data) {
        setData(res.data);
      } else {
        setError(res.error || "Ažuriranje stavke nije uspjelo.");
      }
    },
    []
  );

  const explain = React.useCallback(async (message: string, itemId?: string) => {
    return complianceApi.explain({ message, item_id: itemId });
  }, []);

  return {
    data,
    catalog,
    loading,
    error,
    busy,
    reload: load,
    updateScenarios,
    patchItem,
    explain,
  };
}
