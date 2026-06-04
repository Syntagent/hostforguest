"use client";

import React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Scale, RefreshCw, Bot } from "lucide-react";
import type { DashboardTab } from "@/components/dashboard/dashboard-tabs";
import { ComplianceScenarios } from "./compliance-scenarios";
import { ComplianceChecklist } from "./compliance-checklist";
import { CompliancePdvPanel } from "./compliance-pdv-panel";
import { ComplianceNovasolPanel } from "./compliance-novasol-panel";
import { useCompliance } from "./use-compliance";
import {
  resolveComplianceDeepLink,
  type ComplianceMergedItem,
} from "./compliance-catalog";

type Props = {
  onNavigateTab: (tab: DashboardTab, extraQuery?: string) => void;
};

export function ComplianceTab({ onNavigateTab }: Props) {
  const { data, catalog, loading, error, busy, reload, updateScenarios, patchItem, explain } =
    useCompliance();
  const [showPdvPanel, setShowPdvPanel] = React.useState(false);
  const [showNovasolPanel, setShowNovasolPanel] = React.useState(false);
  const [aiOpen, setAiOpen] = React.useState(false);
  const [aiMessage, setAiMessage] = React.useState("");
  const [aiItemId, setAiItemId] = React.useState<string | undefined>();
  const [aiAnswer, setAiAnswer] = React.useState<string | null>(null);
  const [aiBusy, setAiBusy] = React.useState(false);

  React.useEffect(() => {
    if (data?.scenarios?.in_pdv) {
      setShowPdvPanel(true);
    }
  }, [data?.scenarios?.in_pdv]);

  React.useEffect(() => {
    if (data?.scenarios?.novasol) {
      setShowNovasolPanel(true);
    }
  }, [data?.scenarios?.novasol]);

  const handleScenarioToggle = (id: string, value: boolean) => {
    if (!data) return;
    void updateScenarios({ ...data.scenarios, [id]: value });
  };

  const handleDeepLink = (item: ComplianceMergedItem) => {
    const target = resolveComplianceDeepLink(item.deep_link);
    if (target) {
      onNavigateTab(target.tab, target.query);
    }
  };

  const handleAskAbout = (item: ComplianceMergedItem) => {
    setAiItemId(item.id);
    setAiMessage(`Objasni mi obvezu: ${item.label_hr}`);
    setAiOpen(true);
  };

  const submitAi = async () => {
    if (!aiMessage.trim()) return;
    setAiBusy(true);
    setAiAnswer(null);
    const res = await explain(aiMessage.trim(), aiItemId);
    setAiBusy(false);
    if (res.success && res.data) {
      setAiAnswer(
        `${res.data.answer_hr}\n\n— ${res.data.disclaimer}${res.data.ai_used ? "" : " (bez AI)"}`
      );
    } else {
      setAiAnswer(res.error || "Odgovor trenutno nije dostupan.");
    }
  };

  if (loading) {
    return (
      <div className="w-full animate-pulse space-y-4">
        <div className="h-24 rounded-2xl bg-muted" />
        <div className="h-64 rounded-2xl bg-muted" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="w-full">
        <Alert variant="destructive">
          <AlertTitle>Obveze</AlertTitle>
          <AlertDescription>{error || "Podaci nisu dostupni."}</AlertDescription>
        </Alert>
        <Button className="mt-3" variant="outline" onClick={() => void reload()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Pokušaj ponovo
        </Button>
      </div>
    );
  }

  const scenarios = catalog?.scenarios ?? [];

  return (
    <div className="w-full min-w-0 space-y-4 pb-8 sm:space-y-6">
      <div className="w-full rounded-3xl border border-border bg-card p-4 shadow-sm sm:p-5">
        <div className="flex items-center gap-2">
          <Scale className="h-5 w-5 shrink-0 text-blue-700" />
          <h2 className="text-lg font-semibold text-foreground sm:text-xl">Obveze prema državi</h2>
        </div>
        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
          <p>
            Checklista pomaže da ne zaboravite eVisitor, turističku članarinu, PDV preko Bookinga i
            ostale korake. Nije zamjena za računovođu.
          </p>
          <p className="font-medium text-foreground">
            Napredak: {data.progress.done}/{data.progress.total_relevant} ({data.progress.percent}%)
          </p>
        </div>
      </div>

      <Alert className="w-full border-amber-200 bg-amber-50 text-amber-950">
        <AlertTitle>Informativno — nije porezno-pravni savjet</AlertTitle>
        <AlertDescription>
          Sadržaj je pomoć za pregled obveza. Za odluke i točnost provjerite s ovlaštenim
          računovođom ili pravnikom te službenim izvorima (Porezna, eVisitor, TZ).
        </AlertDescription>
      </Alert>

      <ComplianceScenarios
        scenarios={scenarios}
        active={data.scenarios}
        hints={data.hints}
        disabled={busy}
        onToggle={handleScenarioToggle}
      />

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setShowPdvPanel((v) => !v)}
        >
          {showPdvPanel ? "Sakrij" : "Prikaži"} PDV pravila
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setShowNovasolPanel((v) => !v)}
        >
          {showNovasolPanel ? "Sakrij" : "Prikaži"} Novasol pravila
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => setAiOpen((v) => !v)}>
          <Bot className="mr-1 h-4 w-4" />
          Pitaj o obvezama
        </Button>
      </div>

      {(showPdvPanel || data.scenarios.in_pdv) && (
        <CompliancePdvPanel
          rules={
            data.pdv_regime_rules.length > 0
              ? data.pdv_regime_rules
              : catalog?.pdv_regime_rules ?? []
          }
          forceVisible={showPdvPanel}
        />
      )}

      {(showNovasolPanel || data.scenarios.novasol) && (
        <ComplianceNovasolPanel
          rules={
            data.novasol_regime_rules.length > 0
              ? data.novasol_regime_rules
              : catalog?.novasol_regime_rules ?? []
          }
          forceVisible={showNovasolPanel}
        />
      )}

      {aiOpen ? (
        <div className="w-full rounded-3xl border border-border bg-card p-4 shadow-sm sm:p-5">
          <label className="text-sm font-medium text-gray-900" htmlFor="compliance-ai-input">
            Pitanje (slobodan tekst)
          </label>
          <textarea
            id="compliance-ai-input"
            className="mt-2 w-full rounded-lg border border-border p-2 text-sm"
            rows={3}
            value={aiMessage}
            onChange={(e) => setAiMessage(e.target.value)}
            placeholder="npr. Što trebam kad uđem u PDV preko Bookinga?"
          />
          <div className="mt-2 flex gap-2">
            <Button type="button" size="sm" disabled={aiBusy} onClick={() => void submitAi()}>
              Pošalji
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setAiOpen(false)}>
              Zatvori
            </Button>
          </div>
          {aiAnswer ? (
            <p className="mt-3 whitespace-pre-wrap text-sm text-gray-800">{aiAnswer}</p>
          ) : null}
        </div>
      ) : null}

      <ComplianceChecklist
        categories={data.categories}
        busy={busy}
        onStatusChange={(id, status) => void patchItem(id, status)}
        onDeepLink={handleDeepLink}
        onAskAbout={handleAskAbout}
      />
    </div>
  );
}
