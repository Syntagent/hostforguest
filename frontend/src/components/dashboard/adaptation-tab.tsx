"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";
import { adaptationApi, type AdaptationProject } from "@/lib/api";
import { Bot, CircleHelp, ImagePlus, Palette, RefreshCw, Sparkles, Store } from "lucide-react";

type AssistantTurn = {
  disclaimer: string;
  ai_used: boolean;
  reply: string;
  phases: Array<{
    phase_name: string;
    description: string;
    order: number;
    duration_weeks_min: number;
    duration_weeks_max: number;
    key_tasks: string[];
  }>;
  cost_orientation: string;
  timeline_overview: string;
  communication_tips: string[];
  follow_up_questions: string[];
};

type ChatMessage =
  | { role: "user"; content: string }
  | {
      role: "assistant";
      content: string;
      structured?: AssistantTurn;
      disclaimer?: string;
    };

function StructuredAssistantDetails({
  turn,
  onPickFollowUp,
}: {
  turn: AssistantTurn;
  onPickFollowUp: (q: string) => void;
}) {
  return (
    <details className="mt-3 rounded-md border border-border bg-muted/20 p-2 text-xs">
      <summary className="cursor-pointer select-none font-medium text-foreground">
        Plan details (phases, costs, timeline)
        {turn.ai_used ? " · AI" : " · offline template"} — indicative only
      </summary>
      <div className="mt-2 space-y-3">
        {turn.phases.length > 0 && (
          <div>
            <div className="font-medium text-[11px] mb-1">Suggested path (phases)</div>
            <ol className="list-decimal list-inside space-y-2">
              {[...turn.phases]
                .sort((a, b) => a.order - b.order)
                .map((ph, idx) => (
                  <li key={idx} className="rounded-md bg-muted/40 p-2">
                    <span className="font-medium">{ph.phase_name}</span>
                    {ph.duration_weeks_min > 0 || ph.duration_weeks_max > 0 ? (
                      <span className="text-muted-foreground">
                        {" "}
                        (~{ph.duration_weeks_min}–{ph.duration_weeks_max} wk)
                      </span>
                    ) : null}
                    {ph.description && (
                      <p className="text-muted-foreground mt-1 whitespace-pre-wrap">{ph.description}</p>
                    )}
                    {ph.key_tasks.length > 0 && (
                      <ul className="mt-1 list-disc list-inside text-muted-foreground">
                        {ph.key_tasks.map((t, j) => (
                          <li key={j}>{t}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
            </ol>
          </div>
        )}
        {(turn.cost_orientation || turn.timeline_overview) && (
          <div className="grid gap-2 sm:grid-cols-2">
            {turn.cost_orientation && (
              <div className="rounded-md border border-border p-2">
                <div className="font-medium mb-1">Costs (orientation)</div>
                <p className="text-muted-foreground whitespace-pre-wrap">{turn.cost_orientation}</p>
              </div>
            )}
            {turn.timeline_overview && (
              <div className="rounded-md border border-border p-2">
                <div className="font-medium mb-1">Time</div>
                <p className="text-muted-foreground whitespace-pre-wrap">{turn.timeline_overview}</p>
              </div>
            )}
          </div>
        )}
        {turn.communication_tips.length > 0 && (
          <div>
            <div className="font-medium text-[11px] mb-1">Communication</div>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              {turn.communication_tips.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          </div>
        )}
        {turn.follow_up_questions.length > 0 && (
          <div>
            <div className="font-medium text-[11px] mb-1">Try asking next</div>
            <div className="flex flex-wrap gap-2">
              {turn.follow_up_questions.map((q, i) => (
                <Button
                  key={i}
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="text-xs h-auto py-1.5 whitespace-normal text-left"
                  onClick={() => onPickFollowUp(q)}
                >
                  {q}
                </Button>
              ))}
            </div>
          </div>
        )}
      </div>
    </details>
  );
}

export const AdaptationTab: React.FC = () => {
  const [projects, setProjects] = useState<AdaptationProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [styles, setStyles] = useState("");
  const [busy, setBusy] = useState(false);
  /** Ephemeral notices near the chat composer (errors, short confirmations). */
  const [composerNotice, setComposerNotice] = useState<string | null>(null);
  /** Single source of truth: assistant, tools (analyze / ROI / suppliers / analysis panel). */
  const [activeProjectId, setActiveProjectId] = useState("");
  const [analysisByProject, setAnalysisByProject] = useState<Record<string, Record<string, unknown>>>({});
  const [roiByProject, setRoiByProject] = useState<Record<string, Record<string, unknown>>>({});
  const [adr, setAdr] = useState("120");
  const [occ, setOcc] = useState("45");
  const [assetUrlByProject, setAssetUrlByProject] = useState<Record<string, string>>({});
  const [supplierCatByProject, setSupplierCatByProject] = useState<Record<string, string>>({});
  const [supplierHits, setSupplierHits] = useState<
    Record<
      string,
      Array<{ partner_id: string; name: string; phone: string | null; city: string; distance_km: number | null }>
    >
  >({});
  const [supplierDiscovery, setSupplierDiscovery] = useState<
    Record<
      string,
      { host_has_coordinates: boolean; any_distance_unknown: boolean; sort_explanation: string }
    >
  >({});

  const [assistantDraft, setAssistantDraft] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [notesDraft, setNotesDraft] = useState("");
  const [notesSaving, setNotesSaving] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const activeProject = useMemo(
    () => projects.find((p) => p.id === activeProjectId),
    [projects, activeProjectId]
  );
  const analysis = activeProjectId ? analysisByProject[activeProjectId] : undefined;
  const roi = activeProjectId ? roiByProject[activeProjectId] : undefined;

  const load = useCallback(async () => {
    setLoading(true);
    const r = await adaptationApi.listProjects();
    if (r.success && r.data) setProjects(r.data.projects);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!loading && projects.length === 1 && !activeProjectId) {
      setActiveProjectId(projects[0].id);
    }
  }, [loading, projects, activeProjectId]);

  useEffect(() => {
    const doc = activeProject?.assumptions_json?.project_documentation;
    setNotesDraft(typeof doc === "string" ? doc : "");
  }, [activeProject]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chatMessages, assistantBusy]);

  const create = async () => {
    if (!title.trim()) return;
    setBusy(true);
    setComposerNotice(null);
    const tags = styles
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const r = await adaptationApi.createProject({
      title: title.trim(),
      brief: brief.trim() || undefined,
      style_tags: tags,
      budget_band: "mid",
    });
    setBusy(false);
    if (!r.success) {
      setComposerNotice(r.error || "Could not create project.");
      return;
    }
    setTitle("");
    setBrief("");
    setStyles("");
    await load();
  };

  const analyzeActive = async () => {
    const pid = activeProjectId;
    if (!pid) {
      setComposerNotice("Select a project first.");
      return;
    }
    setBusy(true);
    setComposerNotice(null);
    const r = await adaptationApi.analyze(pid);
    setBusy(false);
    if (!r.success) {
      setComposerNotice(r.error || "Analyze failed.");
      return;
    }
    setAnalysisByProject((prev) => ({ ...prev, [pid]: r.data as Record<string, unknown> }));
    setComposerNotice(
      String((r.data as { disclaimer?: string })?.disclaimer || "Indicative analysis stored.")
    );
  };

  const loadRoiActive = async () => {
    const pid = activeProjectId;
    if (!pid) {
      setComposerNotice("Select a project first.");
      return;
    }
    const r = await adaptationApi.patchRoiInputs(pid, {
      adr: parseFloat(adr) || 0,
      occupancy_pct: parseFloat(occ) || 0,
      adr_uplift_pct: 5,
      occ_uplift_pct: 5,
    });
    if (!r.success) {
      setComposerNotice(r.error || "ROI update failed.");
      return;
    }
    const rr = await adaptationApi.getRoi(pid);
    if (rr.success && rr.data) {
      setRoiByProject((prev) => ({ ...prev, [pid]: rr.data! }));
    }
  };

  const setAssetInput = (projectId: string, v: string) => {
    setAssetUrlByProject((prev) => ({ ...prev, [projectId]: v }));
  };

  const addAssetUrlActive = async () => {
    const pid = activeProjectId;
    if (!pid) {
      setComposerNotice("Select a project first.");
      return;
    }
    const url = (assetUrlByProject[pid] || "").trim();
    if (!url) {
      setComposerNotice("Paste a public HTTPS image URL.");
      return;
    }
    setBusy(true);
    setComposerNotice(null);
    const r = await adaptationApi.addAsset(pid, { storage_url: url, kind: "before_photo" });
    setBusy(false);
    if (!r.success) {
      setComposerNotice(r.error || "Could not add asset.");
      return;
    }
    setComposerNotice("Photo URL added to project.");
    setAssetInput(pid, "");
  };

  const suggestSuppliersActive = async () => {
    const pid = activeProjectId;
    if (!pid) {
      setComposerNotice("Select a project first.");
      return;
    }
    const cat = (supplierCatByProject[pid] || "tiles").trim() || "tiles";
    setBusy(true);
    setComposerNotice(null);
    const r = await adaptationApi.suggestSuppliers(pid, cat);
    setBusy(false);
    if (!r.success || !r.data) {
      setComposerNotice(r.error || "Supplier lookup failed.");
      return;
    }
    setSupplierHits((prev) => ({ ...prev, [pid]: r.data!.partners }));
    if (r.data.discovery) {
      setSupplierDiscovery((prev) => ({ ...prev, [pid]: r.data!.discovery! }));
    }
    setComposerNotice(
      `Mapped “${r.data.bom_category}” → ${r.data.maintenance_category} for partner search.`
    );
  };

  const saveNotes = async () => {
    const pid = activeProjectId;
    if (!pid) return;
    setNotesSaving(true);
    setComposerNotice(null);
    const r = await adaptationApi.patchProject(pid, { documentation_notes: notesDraft });
    setNotesSaving(false);
    if (!r.success) {
      setComposerNotice(r.error || "Could not save notes.");
      return;
    }
    setProjects((prev) => prev.map((p) => (p.id === pid ? r.data! : p)));
    setComposerNotice("Project notes saved.");
  };

  const sendAssistant = async () => {
    const pid = activeProjectId.trim();
    const text = assistantDraft.trim();
    if (!pid || !text) {
      setComposerNotice("Pick a project and enter a question for the assistant.");
      return;
    }
    setAssistantBusy(true);
    setComposerNotice(null);
    const hist = chatMessages.map((m) =>
      m.role === "user"
        ? { role: "user" as const, content: m.content }
        : { role: "assistant" as const, content: m.content }
    );
    const r = await adaptationApi.assistant(pid, {
      message: text,
      history: hist,
    });
    setAssistantBusy(false);
    if (!r.success || !r.data) {
      setComposerNotice(r.error || "Assistant request failed.");
      return;
    }
    const d = r.data;
    setChatMessages((h) => [
      ...h,
      { role: "user", content: text },
      {
        role: "assistant",
        content: d.reply.slice(0, 12000),
        structured: d,
        disclaimer: d.disclaimer,
      },
    ]);
    setAssistantDraft("");
    setComposerNotice(d.disclaimer);
  };

  const clearAssistantChat = () => {
    setChatMessages([]);
    setComposerNotice(null);
  };

  const onAssistantProjectChange = (id: string) => {
    setActiveProjectId(id);
    setChatMessages([]);
    setComposerNotice(null);
  };

  const onComposerKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!assistantBusy) void sendAssistant();
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Adaptation studio
          </CardTitle>
          <CardDescription>
            Plan renovations or fit-outs (kitchen, bath, outdoor, pool, etc.) with indicative BOM ranges and an
            AI coach — not a quote, not legal or structural advice. Add image URLs as assets, then run analysis when
            AI keys are configured.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => load()} disabled={busy}>
              <RefreshCw className="h-4 w-4 mr-1" />
              Refresh
            </Button>
          </div>
          <details className="rounded-md border border-border p-3">
            <summary className="cursor-pointer text-sm font-medium">New project</summary>
            <div className="mt-3 space-y-3">
              <div>
                <label className="text-xs text-muted-foreground">Project title</label>
                <input
                  className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Brief</label>
                <textarea
                  className="mt-1 w-full min-h-[80px] rounded border border-input bg-background px-2 py-2 text-sm"
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Style tags (comma-separated)</label>
                <input
                  className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm"
                  value={styles}
                  onChange={(e) => setStyles(e.target.value)}
                  placeholder="Scandi, wood, sea view"
                />
              </div>
              <Button type="button" disabled={busy} onClick={create}>
                Create project
              </Button>
            </div>
          </details>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(300px,400px)]">
        <Card className="flex flex-col min-h-0">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Bot className="h-5 w-5" />
              Assistant
            </CardTitle>
            <CardDescription>
              Asks use your project brief and the latest BOM from <span className="font-medium">Analyze</span> in
              the tools column. Examples: sequencing trades, what to put in writing, budget bands.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col flex-1 min-h-0 gap-3">
            <div>
              <label htmlFor="adaptation-active-project" className="text-xs text-muted-foreground">
                Active project
              </label>
              <select
                id="adaptation-active-project"
                className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm"
                value={activeProjectId}
                onChange={(e) => onAssistantProjectChange(e.target.value)}
              >
                <option value="">— Select a project —</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>

            {!activeProjectId ? (
              <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
                <p className="font-medium text-foreground mb-1">Welcome</p>
                <p>
                  Create a project above, select it here, then chat or open <strong>Tools</strong> to run analysis,
                  ROI, and supplier ideas. Everything on the right uses the same active project.
                </p>
              </div>
            ) : (
              <div className="min-h-[280px] max-h-[min(58vh,560px)] overflow-y-auto rounded-md border border-border p-3 space-y-3 text-sm">
                {chatMessages.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    Ask anything about sequencing, budgets (indicative), or how to brief installers. If Analyze has
                    not produced lines yet, describe materials and scope in your message.
                  </p>
                )}
                {chatMessages.map((m, i) => (
                  <div
                    key={`${i}-${m.role}`}
                    className={
                      m.role === "user"
                        ? "ml-2 sm:ml-6 rounded-lg bg-muted/60 px-3 py-2"
                        : "mr-2 sm:mr-6 rounded-lg border border-border bg-background px-3 py-2"
                    }
                  >
                    <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                      {m.role === "user" ? "You" : "Assistant"}
                    </div>
                    {m.role === "assistant" ? (
                      <>
                        <MarkdownRenderer content={m.content} className="text-sm" />
                        {m.disclaimer && (
                          <p className="mt-2 text-[10px] text-muted-foreground border-t border-border pt-2">
                            {m.disclaimer}
                          </p>
                        )}
                        {m.structured && (
                          <StructuredAssistantDetails
                            turn={m.structured}
                            onPickFollowUp={(q) => setAssistantDraft(q)}
                          />
                        )}
                      </>
                    ) : (
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    )}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
            )}

            <div>
              <label htmlFor="adaptation-assistant-composer" className="text-xs text-muted-foreground">
                Your message
              </label>
              <textarea
                id="adaptation-assistant-composer"
                aria-label="Message to adaptation assistant"
                className="mt-1 w-full min-h-[96px] rounded border border-input bg-background px-2 py-2 text-sm"
                value={assistantDraft}
                onChange={(e) => setAssistantDraft(e.target.value)}
                onKeyDown={onComposerKeyDown}
                placeholder="e.g. In what order should I schedule bathroom retiling vs electrical work?"
                disabled={assistantBusy || !activeProjectId}
              />
            </div>
            {composerNotice && (
              <p className="text-xs text-amber-800 dark:text-amber-200" role="status">
                {composerNotice}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                disabled={busy || assistantBusy || !activeProjectId}
                onClick={() => void sendAssistant()}
              >
                <Bot className="h-4 w-4 mr-1" />
                Send
              </Button>
              <Button type="button" variant="outline" size="sm" disabled={assistantBusy} onClick={clearAssistantChat}>
                Clear thread
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Tools</CardTitle>
            <CardDescription>
              Analyze, ROI, photos, suppliers, and notes apply to the <span className="font-medium">active project</span>{" "}
              selected in the assistant column.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setShowHelp((v) => !v)}>
                <CircleHelp className="h-4 w-4 mr-1" />
                {showHelp ? "Hide help" : "Help"}
              </Button>
            </div>
            {showHelp && (
              <div className="rounded-md border border-border bg-muted/30 p-3 text-xs space-y-2 text-muted-foreground">
                <p className="font-medium text-foreground">Workflow</p>
                <ol className="list-decimal list-inside space-y-1">
                  <li>Create a project and select it.</li>
                  <li>Optional: add a before photo URL, then run Analyze for an indicative BOM.</li>
                  <li>Use the assistant for sequencing and communication tips.</li>
                  <li>Set ADR/occupancy and recalculate ROI for a rough payback picture.</li>
                  <li>Search suppliers by BOM category (tiles, plumbing, electrical, etc.).</li>
                </ol>
                <p className="font-medium text-foreground pt-1">Glossary</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>
                    <strong className="text-foreground">BOM</strong> — bill of materials: line items with indicative
                    cost ranges.
                  </li>
                  <li>
                    <strong className="text-foreground">Proposal</strong> — stored analysis snapshot (vision + BOM)
                    from Analyze.
                  </li>
                  <li>
                    <strong className="text-foreground">Supplier category</strong> — maps your BOM line to a maintenance
                    partner category for directory search.
                  </li>
                </ul>
                <p className="text-[11px] pt-1">
                  All numbers are indicative; verify with licensed trades and local rules before you commit.
                </p>
              </div>
            )}

            <div className="space-y-2 border-t border-border pt-3">
              <div className="font-medium text-sm">Project notes</div>
              <p className="text-xs text-muted-foreground">
                Saved on the server without replacing your BOM. Use for access codes, contractor contacts, or decisions.
              </p>
              <textarea
                className="w-full min-h-[72px] rounded border border-input bg-background px-2 py-2 text-xs"
                value={notesDraft}
                onChange={(e) => setNotesDraft(e.target.value)}
                disabled={!activeProjectId || notesSaving}
                placeholder={activeProjectId ? "Notes for this project…" : "Select a project first."}
              />
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={!activeProjectId || notesSaving}
                onClick={() => void saveNotes()}
              >
                Save notes
              </Button>
            </div>

            <div className="flex flex-wrap gap-2 border-t border-border pt-3">
              <Button type="button" size="sm" variant="secondary" disabled={busy || !activeProjectId} onClick={analyzeActive}>
                <Sparkles className="h-3 w-3 mr-1" />
                Analyze (AI)
              </Button>
              <Button type="button" size="sm" variant="outline" disabled={busy || !activeProjectId} onClick={loadRoiActive}>
                ROI (sample inputs)
              </Button>
            </div>

            {activeProjectId && analysis && activeProject && (
              <div className="rounded-md border border-border p-3 text-xs space-y-3">
                <div className="font-medium text-sm">Analysis · {activeProject.title}</div>
                {analysis.bom_source === "template_pool" && (
                  <div className="rounded-md bg-sky-950/20 dark:bg-sky-400/10 border border-sky-800/40 px-3 py-2 text-sky-950 dark:text-sky-100">
                    <strong>Template BOM (pool example).</strong> The AI did not return line items (or keys are missing).
                    We filled indicative pool shell finish-out lines — not a quote. Configure AI keys in{" "}
                    <code className="text-[10px]">.env</code> for a fuller breakdown; other project types rely on your
                    brief and AI lines.
                  </div>
                )}
                {analysis.bom_source === "none" && (
                  <div className="rounded-md bg-amber-950/20 dark:bg-amber-400/10 border border-amber-800/40 px-3 py-2 text-amber-950 dark:text-amber-100">
                    <strong>No BOM yet.</strong> Add a richer brief (sizes, materials) and working API keys, then run
                    Analyze again.
                  </div>
                )}
                {analysis.bom_source === "empty_ai" && (
                  <div className="rounded-md bg-amber-950/20 dark:bg-amber-400/10 border border-amber-800/40 px-3 py-2">
                    AI responded but with <strong>zero line items</strong>. Try again or shorten the brief; pool-like
                    briefs may receive a template BOM on the next run if lines stay empty.
                  </div>
                )}
                {analysis.ai_used === true && (
                  <p className="text-emerald-700 dark:text-emerald-400 text-[11px]">
                    Structured AI BOM included — still verify with trades (indicative only).
                  </p>
                )}
                {(() => {
                  const va = analysis.vision_analysis as Record<string, unknown> | undefined;
                  const risks = (va?.risks_and_checks as string[]) || [];
                  const summary = (va?.vision_summary as string) || "";
                  const mood = (va?.mood_board_text as string) || "";
                  return (
                    <>
                      {summary && (
                        <div>
                          <div className="font-medium text-[11px] text-muted-foreground mb-1">Summary</div>
                          <MarkdownRenderer content={summary} className="text-xs" />
                        </div>
                      )}
                      {mood && (
                        <p className="text-muted-foreground">
                          <span className="font-medium text-foreground">Mood / style:</span> {mood}
                        </p>
                      )}
                      {risks.length > 0 && (
                        <div>
                          <div className="font-medium text-[11px] text-muted-foreground mb-1">Risks & checks</div>
                          <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                            {risks.map((x, i) => (
                              <li key={i}>{x}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  );
                })()}
                {(() => {
                  const lines = ((analysis.bom as Record<string, unknown>)?.lines as Record<string, unknown>[]) || [];
                  if (lines.length === 0) {
                    return (
                      <p className="text-muted-foreground italic">
                        No bill-of-material lines in this proposal. Improve the brief and re-analyze, or describe scope
                        in the assistant.
                      </p>
                    );
                  }
                  return (
                    <div className="overflow-x-auto">
                      <div className="font-medium text-[11px] text-muted-foreground mb-1">
                        Bill of materials (indicative EUR)
                      </div>
                      <table className="w-full text-[10px] border-collapse border border-border">
                        <thead>
                          <tr className="bg-muted/50">
                            <th className="border border-border p-1.5 text-left">Section</th>
                            <th className="border border-border p-1.5 text-left">Description</th>
                            <th className="border border-border p-1.5 text-right">Min</th>
                            <th className="border border-border p-1.5 text-right">Max</th>
                            <th className="border border-border p-1.5 text-left">Supplier cat.</th>
                          </tr>
                        </thead>
                        <tbody>
                          {lines.map((row, i) => (
                            <tr key={i}>
                              <td className="border border-border p-1.5 align-top">{String(row.section ?? "")}</td>
                              <td className="border border-border p-1.5 align-top">{String(row.description ?? "")}</td>
                              <td className="border border-border p-1.5 text-right align-top">
                                {Number(row.cost_min_eur ?? 0).toLocaleString()}
                              </td>
                              <td className="border border-border p-1.5 text-right align-top">
                                {Number(row.cost_max_eur ?? 0).toLocaleString()}
                              </td>
                              <td className="border border-border p-1.5 align-top text-muted-foreground">
                                {String(row.supplier_category ?? "")}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="mt-2 text-muted-foreground">
                        Range total (min–max):{" "}
                        <strong>
                          {analysis.total_range_min != null
                            ? Number(analysis.total_range_min).toLocaleString()
                            : "—"}
                        </strong>
                        {" – "}
                        <strong>
                          {analysis.total_range_max != null
                            ? Number(analysis.total_range_max).toLocaleString()
                            : "—"}{" "}
                          €
                        </strong>
                      </p>
                    </div>
                  );
                })()}
                {Array.isArray(analysis.hints) && (analysis.hints as string[]).length > 0 && (
                  <ul className="list-disc list-inside text-muted-foreground space-y-0.5">
                    {(analysis.hints as string[]).map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                )}
                <details className="text-[10px] text-muted-foreground">
                  <summary className="cursor-pointer select-none">Technical JSON</summary>
                  <pre className="whitespace-pre-wrap overflow-auto max-h-48 bg-muted p-2 rounded mt-1">
                    {JSON.stringify(analysis, null, 2)}
                  </pre>
                </details>
              </div>
            )}

            {activeProjectId && roi && (
              <div className="rounded-md border border-border p-3 text-xs space-y-2">
                <div className="font-medium text-sm">ROI (indicative)</div>
                <p className="text-muted-foreground text-[11px]">
                  Set ADR and occupancy, then use <strong>ROI (sample inputs)</strong> or <strong>Recalculate</strong>.
                  Payback needs incremental revenue and a non-zero investment from your BOM mid-range.
                </p>
                <div className="grid sm:grid-cols-2 gap-2 mt-2">
                  <label>
                    ADR (€)
                    <input
                      className="mt-1 w-full rounded border px-2 py-1"
                      value={adr}
                      onChange={(e) => setAdr(e.target.value)}
                    />
                  </label>
                  <label>
                    Occupancy %
                    <input
                      className="mt-1 w-full rounded border px-2 py-1"
                      value={occ}
                      onChange={(e) => setOcc(e.target.value)}
                    />
                  </label>
                </div>
                <Button type="button" size="sm" className="mt-2" variant="outline" onClick={loadRoiActive}>
                  Recalculate ROI
                </Button>
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 mt-3 text-[11px]">
                  <dt className="text-muted-foreground">Baseline revenue / year</dt>
                  <dd>{Number(roi.baseline_revenue_year ?? 0).toLocaleString()} €</dd>
                  <dt className="text-muted-foreground">Projected revenue / year (with uplift)</dt>
                  <dd>{Number(roi.projected_revenue_year ?? 0).toLocaleString()} €</dd>
                  <dt className="text-muted-foreground">Incremental / year</dt>
                  <dd>{Number(roi.incremental_revenue_year ?? 0).toLocaleString()} €</dd>
                  <dt className="text-muted-foreground">Simple payback (months)</dt>
                  <dd>
                    {roi.simple_payback_months != null
                      ? Number(roi.simple_payback_months).toFixed(1)
                      : "— (need incremental € and investment from BOM)"}
                  </dd>
                </dl>
                <details className="text-[10px] text-muted-foreground mt-2">
                  <summary className="cursor-pointer select-none">Technical JSON</summary>
                  <pre className="whitespace-pre-wrap overflow-auto max-h-40 bg-muted p-2 rounded mt-1">
                    {JSON.stringify(roi, null, 2)}
                  </pre>
                </details>
              </div>
            )}

            <div className="space-y-2 border-t border-border pt-3">
              <div className="font-medium text-sm">Before photo URL</div>
              <div className="flex flex-wrap gap-2">
                <input
                  className="flex-1 min-w-[180px] rounded border border-input bg-background px-2 py-1 text-xs"
                  value={activeProjectId ? assetUrlByProject[activeProjectId] || "" : ""}
                  onChange={(e) => activeProjectId && setAssetInput(activeProjectId, e.target.value)}
                  placeholder="https://…"
                  disabled={!activeProjectId}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={busy || !activeProjectId}
                  onClick={() => void addAssetUrlActive()}
                >
                  <ImagePlus className="h-3 w-3 mr-1" />
                  Add photo
                </Button>
              </div>
            </div>

            <div className="space-y-2 border-t border-border pt-3">
              <div className="font-medium text-sm">Suppliers</div>
              <p className="text-xs text-muted-foreground">
                Results are <span className="font-medium text-foreground">directory partners</span>, not automatic
                quotes. Ranking favors partners linked to you, then same city, then distance when coordinates exist on
                both sides.
              </p>
              {activeProjectId && supplierDiscovery[activeProjectId] && (
                <p className="text-[11px] text-muted-foreground border-l-2 border-border pl-2">
                  {supplierDiscovery[activeProjectId].sort_explanation}
                  {!supplierDiscovery[activeProjectId].host_has_coordinates && (
                    <span className="block mt-1 text-amber-800 dark:text-amber-200">
                      Your host profile has no map coordinates — distances may be missing; treat order as approximate.
                    </span>
                  )}
                  {supplierDiscovery[activeProjectId].any_distance_unknown && (
                    <span className="block mt-1">
                      Some rows show no km — that means distance was not computed, not that they are far away.
                    </span>
                  )}
                </p>
              )}
              <label className="text-xs text-muted-foreground">BOM / supplier category</label>
              <div className="flex flex-wrap gap-2">
                <input
                  className="flex-1 min-w-[120px] rounded border border-input bg-background px-2 py-1 text-xs"
                  value={activeProjectId ? supplierCatByProject[activeProjectId] ?? "tiles" : ""}
                  onChange={(e) =>
                    activeProjectId &&
                    setSupplierCatByProject((prev) => ({ ...prev, [activeProjectId]: e.target.value }))
                  }
                  placeholder="tiles, plumbing, electrical, pool…"
                  disabled={!activeProjectId}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={busy || !activeProjectId}
                  onClick={() => void suggestSuppliersActive()}
                >
                  <Store className="h-3 w-3 mr-1" />
                  Suggest suppliers
                </Button>
              </div>
              {activeProjectId && (supplierHits[activeProjectId] || []).length > 0 && (
                <ul className="text-xs space-y-1 border border-border rounded-md p-2 bg-muted/20">
                  {supplierHits[activeProjectId]!.map((sp) => (
                    <li key={sp.partner_id}>
                      <span className="font-medium">{sp.name}</span>
                      {sp.phone && <span className="text-muted-foreground ml-2">{sp.phone}</span>}
                      <span className="text-muted-foreground ml-2">
                        {sp.city}
                        {sp.distance_km != null ? ` · ${sp.distance_km.toFixed(1)} km` : " · distance n/a"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="border-t border-border pt-3 text-xs text-muted-foreground">
              {loading ? (
                <p>Loading projects…</p>
              ) : projects.length === 0 ? (
                <p>No projects yet — use <strong>New project</strong> above.</p>
              ) : (
                <p>
                  {projects.length} project{projects.length === 1 ? "" : "s"} — switch the active one in the assistant
                  column.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
