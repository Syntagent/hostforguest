"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { channelIntegrationsApi, type ChannelAccountDto } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export const ChannelIntegrationPanel: React.FC = () => {
  const { user: currentHost } = useAuth();
  const [account, setAccount] = useState<ChannelAccountDto | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({
    hotel_id: "",
    api_username: "",
    api_password: "",
  });
  const [mapRoom, setMapRoom] = useState({ external_room_id: "", external_rate_id: "" });
  const [pushAvail, setPushAvail] = useState({
    mapping_id: "",
    date_from: "",
    date_to: "",
    available: 1,
  });
  const [pushRates, setPushRates] = useState({
    mapping_id: "",
    date_from: "",
    date_to: "",
    price: 100,
    currency: "EUR",
  });

  const loadStatus = useCallback(async () => {
    if (!currentHost) return;
    const r = await channelIntegrationsApi.getStatus();
    if (!r.success || !r.data) {
      setAccount(null);
      setHealth(null);
      setMessage(r.error || "Cannot load channel integration status. Verify backend/API connection.");
      return;
    }
    setMessage(null);
    const acc = r.data.account;
    setAccount(acc);
    if (acc) {
      const h = await channelIntegrationsApi.getHealth(acc.id);
      if (h.success && h.data) {
        setHealth(h.data as Record<string, unknown>);
      } else {
        setHealth(null);
      }
    } else {
      setHealth(null);
    }
  }, [currentHost]);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const connect = async () => {
    setBusy(true);
    setMessage(null);
    const r = await channelIntegrationsApi.connectBookingCom({
      hotel_id: form.hotel_id.trim(),
      api_username: form.api_username.trim(),
      api_password: form.api_password,
    });
    setBusy(false);
    if (!r.success) {
      setMessage(r.error || "Connect failed");
      return;
    }
    setMessage("Connected to Booking.com channel.");
    setForm((f) => ({ ...f, api_password: "" }));
    await loadStatus();
  };

  const disconnect = async () => {
    setBusy(true);
    setMessage(null);
    const r = await channelIntegrationsApi.disconnect();
    setBusy(false);
    if (!r.success) {
      setMessage(r.error || "Disconnect failed");
      return;
    }
    setAccount(null);
    setHealth(null);
    setMessage("Disconnected.");
    await loadStatus();
  };

  const syncRes = async () => {
    if (!account) return;
    setBusy(true);
    const r = await channelIntegrationsApi.syncReservations(account.id);
    setBusy(false);
    setMessage(r.success ? JSON.stringify(r.data) : r.error || "Sync failed");
    await loadStatus();
  };

  const addMapping = async () => {
    if (!account || !currentHost) return;
    setBusy(true);
    const r = await channelIntegrationsApi.createMapping(account.id, {
      local_entity_type: "host",
      local_entity_id: currentHost.id,
      external_room_id: mapRoom.external_room_id.trim(),
      external_rate_id: mapRoom.external_rate_id.trim() || undefined,
    });
    setBusy(false);
    if (r.success && r.data) {
      setMessage(`Mapping created. id=${r.data.id} — use this UUID for push calls.`);
      setPushAvail((p) => ({ ...p, mapping_id: r.data!.id }));
      setPushRates((p) => ({ ...p, mapping_id: r.data!.id }));
    } else {
      setMessage(r.error || "Mapping failed");
    }
  };

  const doPushAvail = async () => {
    if (!account) return;
    setBusy(true);
    const r = await channelIntegrationsApi.pushAvailability(account.id, {
      mapping_id: pushAvail.mapping_id.trim(),
      date_from: pushAvail.date_from,
      date_to: pushAvail.date_to,
      available: pushAvail.available,
    });
    setBusy(false);
    setMessage(r.success ? "Availability pushed." : r.error || "Push failed");
  };

  const doPushRates = async () => {
    if (!account) return;
    setBusy(true);
    const r = await channelIntegrationsApi.pushRates(account.id, {
      mapping_id: pushRates.mapping_id.trim(),
      date_from: pushRates.date_from,
      date_to: pushRates.date_to,
      price: pushRates.price,
      currency: pushRates.currency,
    });
    setBusy(false);
    setMessage(r.success ? "Rates pushed." : r.error || "Push failed");
  };

  if (!currentHost) {
    return (
      <Card>
        <CardContent className="pt-6 text-sm text-gray-500">
          Sign in to manage Booking.com sync.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Booking.com</CardTitle>
          <CardDescription>
            Connect your property, map rooms, pull reservations, and push availability/rates (complementary to
            Booking.com extranet).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {message && (
            <p className="text-sm rounded-md bg-slate-50 border border-slate-200 p-2 whitespace-pre-wrap">
              {message}
            </p>
          )}
          {!account ? (
            <div className="grid gap-3 max-w-md">
              <label className="text-sm font-medium">Hotel / property ID</label>
              <input
                className="border rounded px-3 py-2 text-sm"
                value={form.hotel_id}
                onChange={(e) => setForm({ ...form, hotel_id: e.target.value })}
                placeholder="From Booking.com extranet"
              />
              <label className="text-sm font-medium">API username</label>
              <input
                className="border rounded px-3 py-2 text-sm"
                value={form.api_username}
                onChange={(e) => setForm({ ...form, api_username: e.target.value })}
              />
              <label className="text-sm font-medium">API password</label>
              <input
                type="password"
                className="border rounded px-3 py-2 text-sm"
                value={form.api_password}
                onChange={(e) => setForm({ ...form, api_password: e.target.value })}
              />
              <Button onClick={() => void connect()} disabled={busy}>
                {busy ? "Connecting…" : "Connect"}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm">
                Status: <strong>{account.status}</strong> · Hotel ID:{" "}
                <code>{account.external_hotel_id || "—"}</code>
              </p>
              {health && (
                <ul className="text-xs text-gray-600 space-y-1">
                  <li>Last poll: {String(health.last_reservations_poll_at ?? "—")}</li>
                  <li>Last full sync: {String(health.last_full_sync_at ?? "—")}</li>
                  <li>Errors in a row: {String(health.consecutive_errors ?? 0)}</li>
                  <li>Last error: {String(health.last_error ?? "—")}</li>
                </ul>
              )}
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => void syncRes()} disabled={busy}>
                  Sync reservations
                </Button>
                <Button variant="outline" onClick={() => void loadStatus()} disabled={busy}>
                  Refresh health
                </Button>
                <Button variant="danger" onClick={() => void disconnect()} disabled={busy}>
                  Disconnect
                </Button>
              </div>

              <div className="border-t pt-4 space-y-2">
                <h4 className="text-sm font-semibold">Room mapping</h4>
                <p className="text-xs text-gray-500">
                  Link this host to a Booking.com room id. After saving, use the returned mapping UUID for pushes.
                </p>
                <div className="grid gap-2 max-w-lg">
                  <input
                    className="border rounded px-3 py-2 text-sm"
                    placeholder="External room ID"
                    value={mapRoom.external_room_id}
                    onChange={(e) => setMapRoom({ ...mapRoom, external_room_id: e.target.value })}
                  />
                  <input
                    className="border rounded px-3 py-2 text-sm"
                    placeholder="Optional rate ID"
                    value={mapRoom.external_rate_id}
                    onChange={(e) => setMapRoom({ ...mapRoom, external_rate_id: e.target.value })}
                  />
                  <Button variant="secondary" onClick={() => void addMapping()} disabled={busy}>
                    Save mapping
                  </Button>
                </div>
              </div>

              <div className="border-t pt-4 grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold">Push availability</h4>
                  <input
                    className="border rounded px-3 py-2 text-sm w-full"
                    placeholder="Mapping UUID"
                    value={pushAvail.mapping_id}
                    onChange={(e) => setPushAvail({ ...pushAvail, mapping_id: e.target.value })}
                  />
                  <div className="flex gap-2">
                    <input
                      type="date"
                      className="border rounded px-2 py-1 text-sm flex-1"
                      value={pushAvail.date_from}
                      onChange={(e) => setPushAvail({ ...pushAvail, date_from: e.target.value })}
                    />
                    <input
                      type="date"
                      className="border rounded px-2 py-1 text-sm flex-1"
                      value={pushAvail.date_to}
                      onChange={(e) => setPushAvail({ ...pushAvail, date_to: e.target.value })}
                    />
                  </div>
                  <input
                    type="number"
                    min={0}
                    className="border rounded px-3 py-2 text-sm w-full"
                    value={pushAvail.available}
                    onChange={(e) =>
                      setPushAvail({ ...pushAvail, available: parseInt(e.target.value, 10) || 0 })
                    }
                  />
                  <Button variant="outline" size="sm" onClick={() => void doPushAvail()} disabled={busy}>
                    Push availability
                  </Button>
                </div>
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold">Push rates</h4>
                  <input
                    className="border rounded px-3 py-2 text-sm w-full"
                    placeholder="Mapping UUID"
                    value={pushRates.mapping_id}
                    onChange={(e) => setPushRates({ ...pushRates, mapping_id: e.target.value })}
                  />
                  <div className="flex gap-2">
                    <input
                      type="date"
                      className="border rounded px-2 py-1 text-sm flex-1"
                      value={pushRates.date_from}
                      onChange={(e) => setPushRates({ ...pushRates, date_from: e.target.value })}
                    />
                    <input
                      type="date"
                      className="border rounded px-2 py-1 text-sm flex-1"
                      value={pushRates.date_to}
                      onChange={(e) => setPushRates({ ...pushRates, date_to: e.target.value })}
                    />
                  </div>
                  <input
                    type="number"
                    className="border rounded px-3 py-2 text-sm w-full"
                    value={pushRates.price}
                    onChange={(e) =>
                      setPushRates({ ...pushRates, price: parseFloat(e.target.value) || 0 })
                    }
                  />
                  <Button variant="outline" size="sm" onClick={() => void doPushRates()} disabled={busy}>
                    Push rates
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
