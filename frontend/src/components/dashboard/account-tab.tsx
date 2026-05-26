"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { authApi } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { Eye, EyeOff, Loader2, LogOut, Shield, Trash2 } from "lucide-react";

interface SessionRow {
  id?: string;
  created_at?: string;
  expires_at?: string;
  user_agent?: string | null;
  ip_address?: string | null;
  is_active?: boolean;
}

export function AccountTab() {
  const { user, logout, logoutAllDevices, clearError } = useAuth();
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);

  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [showDelete, setShowDelete] = useState(false);

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    const res = await authApi.getSessions();
    if (res.success && res.data && typeof res.data === "object") {
      const payload = res.data as { sessions?: SessionRow[] };
      setSessions(Array.isArray(payload.sessions) ? payload.sessions : []);
    } else {
      setSessions([]);
    }
    setSessionsLoading(false);
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    clearError();

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    setBusy(true);
    const res = await authApi.changePassword(currentPassword, newPassword);
    setBusy(false);

    if (res.success) {
      setMessage("Password updated. Sign in again on other devices if needed.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } else {
      setError(res.error || "Could not update password.");
    }
  };

  const handleLogoutAll = async () => {
    setError(null);
    setMessage(null);
    setBusy(true);
    const ok = await logoutAllDevices();
    setBusy(false);
    if (!ok) {
      setError("Could not sign out from all devices.");
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirm !== user?.email) {
      setError("Type your email exactly to confirm account deletion.");
      return;
    }
    setError(null);
    setBusy(true);
    const res = await authApi.deleteAccount();
    setBusy(false);
    if (res.success || res.status === 204) {
      await logout();
      return;
    }
    setError(res.error || "Could not delete account.");
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Account
          </CardTitle>
          <CardDescription>
            Signed in as <strong>{user?.email}</strong>
            {user?.full_name ? ` · ${user.full_name}` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {message && (
            <Alert>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          )}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void logout()} disabled={busy}>
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </Button>
            <Button variant="outline" onClick={() => void handleLogoutAll()} disabled={busy}>
              Sign out all devices
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
          <CardDescription>Update your sign-in password (min. 8 characters).</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleChangePassword(e)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="current-password">Current password</Label>
              <Input
                id="current-password"
                type={showPasswords ? "text" : "password"}
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-password">New password</Label>
              <Input
                id="new-password"
                type={showPasswords ? "text" : "password"}
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirm new password</Label>
              <div className="relative">
                <Input
                  id="confirm-password"
                  type={showPasswords ? "text" : "password"}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                  className="pr-10"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  onClick={() => setShowPasswords((v) => !v)}
                  aria-label={showPasswords ? "Hide passwords" : "Show passwords"}
                >
                  {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Update password
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active sessions</CardTitle>
          <CardDescription>Devices where you are currently signed in.</CardDescription>
        </CardHeader>
        <CardContent>
          {sessionsLoading ? (
            <p className="text-sm text-muted-foreground">Loading sessions…</p>
          ) : sessions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active sessions found.</p>
          ) : (
            <ul className="space-y-3 text-sm">
              {sessions.map((s, i) => (
                <li key={s.id || i} className="rounded-xl border border-border p-3">
                  <p className="font-medium truncate">{s.user_agent || "Unknown device"}</p>
                  <p className="text-muted-foreground text-xs mt-1">
                    {s.ip_address ? `IP ${s.ip_address} · ` : ""}
                    {s.created_at ? `Started ${new Date(s.created_at).toLocaleString()}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
          <Button variant="ghost" size="sm" className="mt-3" onClick={() => void loadSessions()}>
            Refresh
          </Button>
        </CardContent>
      </Card>

      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2">
            <Trash2 className="h-5 w-5" />
            Delete account
          </CardTitle>
          <CardDescription>
            Deactivates your host account. This cannot be undone from the UI.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {!showDelete ? (
            <Button variant="destructive" onClick={() => setShowDelete(true)}>
              Delete my account
            </Button>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                Type <strong>{user?.email}</strong> to confirm:
              </p>
              <Input
                value={deleteConfirm}
                onChange={(e) => setDeleteConfirm(e.target.value)}
                placeholder={user?.email}
                autoComplete="off"
              />
              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  disabled={busy || deleteConfirm !== user?.email}
                  onClick={() => void handleDeleteAccount()}
                >
                  Confirm deletion
                </Button>
                <Button variant="outline" onClick={() => { setShowDelete(false); setDeleteConfirm(""); }}>
                  Cancel
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
