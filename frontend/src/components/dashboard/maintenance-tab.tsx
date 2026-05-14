"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  maintenanceApi,
  type MaintenanceIssue,
} from "@/lib/api";
import { Wrench, RefreshCw, Sparkles, Copy, CalendarClock, CheckCircle, MessageSquareText } from "lucide-react";

type ScheduleRow = {
  id: string;
  title: string;
  category: string;
  interval_days: number;
  active: boolean;
  last_run_at: string | null;
  next_due_at: string | null;
};

export const MaintenanceTab: React.FC = () => {
  const [issues, setIssues] = useState<MaintenanceIssue[]>([]);
  const [schedules, setSchedules] = useState<ScheduleRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("plumbing");
  const [description, setDescription] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [partners, setPartners] = useState<
    Array<{ partner_id: string; name: string; phone: string | null; reason: string }>
  >([]);
  const [draft, setDraft] = useState<string | null>(null);
  const [draftPartnerId, setDraftPartnerId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [schTitle, setSchTitle] = useState("");
  const [schCategory, setSchCategory] = useState("hvac");
  const [schInterval, setSchInterval] = useState("180");
  const [replyPaste, setReplyPaste] = useState("");
  const [replySugs, setReplySugs] = useState<string[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    const [c, i, s] = await Promise.all([
      maintenanceApi.getCategories(),
      maintenanceApi.listIssues(),
      maintenanceApi.listSchedules(),
    ]);
    if (c.success && c.data) setCategories(c.data.categories);
    if (i.success && i.data) setIssues(i.data.issues);
    if (s.success && s.data) setSchedules(s.data.schedules);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const create = async () => {
    if (!title.trim()) {
      setMsg("Title required");
      return;
    }
    setBusy(true);
    setMsg(null);
    const r = await maintenanceApi.createIssue({
      category,
      title: title.trim(),
      description: description.trim() || undefined,
    });
    setBusy(false);
    if (!r.success) {
      setMsg(r.error || "Failed");
      return;
    }
    setTitle("");
    setDescription("");
    await load();
  };

  const createSchedule = async () => {
    if (!schTitle.trim()) {
      setMsg("Schedule title required");
      return;
    }
    const days = parseInt(schInterval, 10);
    if (!days || days < 1) {
      setMsg("Interval must be at least 1 day");
      return;
    }
    setBusy(true);
    setMsg(null);
    const r = await maintenanceApi.createSchedule({
      title: schTitle.trim(),
      category: schCategory,
      interval_days: days,
    });
    setBusy(false);
    if (!r.success) {
      setMsg(r.error || "Schedule failed");
      return;
    }
    setSchTitle("");
    setMsg("Preventive schedule created.");
    await load();
  };

  const suggest = async (issueId: string) => {
    setBusy(true);
    setSelectedId(issueId);
    setPartners([]);
    setDraft(null);
    setDraftPartnerId(null);
    setReplySugs([]);
    const r = await maintenanceApi.suggestPartners(issueId);
    setBusy(false);
    if (!r.success || !r.data) {
      setMsg(r.error || "Suggest failed");
      return;
    }
    setPartners(r.data.ranked);
    setMsg(r.data.disclaimer);
  };

  const genDraft = async (issueId: string, partnerId: string) => {
    setBusy(true);
    setDraftPartnerId(partnerId);
    const r = await maintenanceApi.draftMessage(issueId, { partner_id: partnerId });
    setBusy(false);
    if (!r.success || !r.data) {
      setMsg(r.error || "Draft failed");
      return;
    }
    setDraft(r.data.message_hr);
  };

  const saveDraftLog = async (issueId: string) => {
    if (!draft?.trim() || !draftPartnerId) return;
    setBusy(true);
    const r = await maintenanceApi.saveDraft(issueId, {
      partner_id: draftPartnerId,
      draft_text: draft,
      channel: "whatsapp",
      host_edited: true,
    });
    setBusy(false);
    setMsg(r.success ? "Draft saved to log." : r.error || "Save failed");
  };

  const resolveIssue = async (issueId: string) => {
    setBusy(true);
    const r = await maintenanceApi.patchIssue(issueId, { status: "resolved" });
    setBusy(false);
    if (!r.success) {
      setMsg(r.error || "Could not resolve");
      return;
    }
    setSelectedId(null);
    setDraft(null);
    await load();
  };

  const fetchReplySuggestions = async (issueId: string) => {
    if (!replyPaste.trim()) return;
    setBusy(true);
    const r = await maintenanceApi.replySuggestions(issueId, replyPaste.trim());
    setBusy(false);
    if (!r.success || !r.data) {
      setMsg(r.error || "Reply suggestions failed");
      return;
    }
    setReplySugs(r.data.suggestions || []);
  };

  const runPrev = async () => {
    setBusy(true);
    const r = await maintenanceApi.runPreventive();
    setBusy(false);
    if (r.success && r.data) {
      setMsg(`Preventive: created ${r.data.created_count} issue(s).`);
      await load();
    } else setMsg(r.error || "Failed");
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wrench className="h-5 w-5" />
            Maintenance
          </CardTitle>
          <CardDescription>
            Track issues, run preventive schedules, and get assistive partner suggestions (verify
            contractors yourself).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {msg && <p className="text-sm text-amber-700 dark:text-amber-300">{msg}</p>}
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => load()}>
              <RefreshCw className="h-4 w-4 mr-1" />
              Refresh
            </Button>
            <Button type="button" variant="secondary" size="sm" disabled={busy} onClick={runPrev}>
              Run due preventive
            </Button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs text-muted-foreground">Category</label>
              <select
                className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {(categories.length ? categories : ["plumbing", "electrical", "hvac", "other"]).map(
                  (c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  )
                )}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Title</label>
              <input
                className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Leak under sink"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Description</label>
            <textarea
              className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm min-h-[72px]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <Button type="button" disabled={busy} onClick={create}>
            Create issue
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarClock className="h-5 w-5" />
            Preventive schedules
          </CardTitle>
          <CardDescription>
            Recurring reminders; use &quot;Run due preventive&quot; to open issues when due.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="sm:col-span-1">
              <label className="text-xs text-muted-foreground">Title</label>
              <input
                className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm"
                value={schTitle}
                onChange={(e) => setSchTitle(e.target.value)}
                placeholder="e.g. AC filter check"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Category</label>
              <select
                className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm"
                value={schCategory}
                onChange={(e) => setSchCategory(e.target.value)}
              >
                {(categories.length ? categories : ["hvac", "plumbing", "safety"]).map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Every (days)</label>
              <input
                type="number"
                min={1}
                className="mt-1 w-full rounded border border-input bg-background px-2 py-2 text-sm"
                value={schInterval}
                onChange={(e) => setSchInterval(e.target.value)}
              />
            </div>
          </div>
          <Button type="button" variant="secondary" size="sm" disabled={busy} onClick={createSchedule}>
            Add schedule
          </Button>
          {schedules.length > 0 && (
            <ul className="text-xs space-y-1 border-t border-border pt-3 mt-2">
              {schedules.map((s) => (
                <li key={s.id} className="flex flex-wrap justify-between gap-1 text-muted-foreground">
                  <span className="font-medium text-foreground">{s.title}</span>
                  <span>
                    {s.category} · every {s.interval_days}d
                    {s.next_due_at && ` · next ${new Date(s.next_due_at).toLocaleDateString()}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Issues</CardTitle>
          <CardDescription>Guest reports appear with source &quot;guest&quot;.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : issues.length === 0 ? (
            <p className="text-sm text-muted-foreground">No issues yet.</p>
          ) : (
            <ul className="space-y-3">
              {issues.map((iss) => (
                <li
                  key={iss.id}
                  className="rounded-lg border border-border p-3 text-sm flex flex-col gap-2"
                >
                  <div className="flex flex-wrap justify-between gap-2">
                    <span className="font-medium">{iss.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {iss.category} · {iss.status} · {iss.source}
                    </span>
                  </div>
                  {iss.description && (
                    <p className="text-muted-foreground whitespace-pre-wrap">{iss.description}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={busy || iss.status === "resolved"}
                      onClick={() => suggest(iss.id)}
                    >
                      <Sparkles className="h-3 w-3 mr-1" />
                      Suggest partners
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={busy || iss.status === "resolved"}
                      onClick={() => resolveIssue(iss.id)}
                    >
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Mark resolved
                    </Button>
                  </div>
                  {selectedId === iss.id && partners.length > 0 && (
                    <div className="mt-2 space-y-2 border-t border-border pt-2">
                      {partners.map((p) => (
                        <div
                          key={p.partner_id}
                          className="flex flex-wrap items-center justify-between gap-2 text-xs"
                        >
                          <div>
                            <span className="font-medium">{p.name}</span>
                            {p.phone && <span className="ml-2 text-muted-foreground">{p.phone}</span>}
                            <p className="text-muted-foreground">{p.reason}</p>
                          </div>
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            disabled={busy}
                            onClick={() => genDraft(iss.id, p.partner_id)}
                          >
                            Draft message (HR)
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                  {selectedId === iss.id && draft && (
                    <div className="mt-2 rounded bg-muted p-2 text-xs whitespace-pre-wrap space-y-2">
                      {draft}
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => void navigator.clipboard.writeText(draft)}
                        >
                          <Copy className="h-3 w-3 mr-1" />
                          Copy
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          disabled={busy || !draftPartnerId}
                          onClick={() => saveDraftLog(iss.id)}
                        >
                          Save draft log
                        </Button>
                      </div>
                    </div>
                  )}
                  {selectedId === iss.id && (
                    <div className="mt-2 border-t border-border pt-2 space-y-2">
                      <p className="text-xs font-medium flex items-center gap-1">
                        <MessageSquareText className="h-3 w-3" />
                        Reply assistant (paste majstor message)
                      </p>
                      <textarea
                        className="w-full rounded border border-input bg-background px-2 py-2 text-xs min-h-[64px]"
                        value={replyPaste}
                        onChange={(e) => setReplyPaste(e.target.value)}
                        placeholder="Paste incoming message…"
                      />
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={busy}
                        onClick={() => fetchReplySuggestions(iss.id)}
                      >
                        Suggest replies (HR)
                      </Button>
                      {replySugs.length > 0 && (
                        <ul className="text-xs space-y-1 list-disc pl-4">
                          {replySugs.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
