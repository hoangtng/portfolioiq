"use client";

import { useEffect, useState } from "react";
import { Bell, BellOff, Plus, Trash2, Loader2 } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader, EmptyState, Spinner, Pill } from "@/components/ui";
import { portfolio, ApiError } from "@/lib/api";
import { fmtCurrency, fmtDate, timeAgo } from "@/lib/utils";
import type { PriceAlert } from "@/types";

export default function AlertsPage() {
  return (<AppShell><Alerts /></AppShell>);
}

function Alerts() {
  const [tab, setTab] = useState<"active" | "triggered">("active");
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [loading, setLoading] = useState(true);

  const [ticker, setTicker]         = useState("");
  const [condition, setCondition]   = useState<"above" | "below">("above");
  const [targetPrice, setTargetPrice] = useState("");
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await portfolio.alerts();
      setAlerts(data.results);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const filtered = alerts.filter((a) => tab === "active" ? a.is_active : !a.is_active);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(""); setCreating(true);
    try {
      await portfolio.createAlert({ ticker, condition, target_price: targetPrice });
      setTicker(""); setTargetPrice("");
      load();
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.message : "Failed to create alert");
    } finally { setCreating(false); }
  };

  const onDelete = async (id: number) => {
    if (!confirm("Delete this alert?")) return;
    try {
      await portfolio.deleteAlert(id);
      load();
    } catch (e) { console.error(e); }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1100px] mx-auto">
      <PageHeader
        title="Alerts"
        subtitle="Price targets · Checked every 60s · Telegram on trigger"
      />

      {/* Create form */}
      <div className="card p-5 mb-6">
        <h3 className="section-title mb-4">New alert</h3>
        <form onSubmit={onCreate} className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr_auto] gap-3 items-end">
          <div>
            <label className="label">ticker</label>
            <input type="text" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
              required placeholder="PLTR" className="input font-mono" />
          </div>
          <div>
            <label className="label">condition</label>
            <select value={condition} onChange={(e) => setCondition(e.target.value as "above" | "below")} className="input">
              <option value="above">above</option>
              <option value="below">below</option>
            </select>
          </div>
          <div>
            <label className="label">target price</label>
            <input type="number" value={targetPrice} onChange={(e) => setTargetPrice(e.target.value)}
              required step="0.01" placeholder="25.00" className="input font-mono" />
          </div>
          <button type="submit" disabled={creating} className="btn-primary h-[42px]">
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Create
          </button>
        </form>
        {createError && (
          <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg mt-3">! {createError}</div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-bg-card border border-line rounded-lg p-1 mb-4 max-w-xs">
        <button onClick={() => setTab("active")}
          className={`flex-1 py-2 text-xs font-mono rounded ${tab === "active" ? "bg-accent/10 text-accent" : "text-ink-muted"}`}>
          Active ({alerts.filter((a) => a.is_active).length})
        </button>
        <button onClick={() => setTab("triggered")}
          className={`flex-1 py-2 text-xs font-mono rounded ${tab === "triggered" ? "bg-accent/10 text-accent" : "text-ink-muted"}`}>
          Triggered ({alerts.filter((a) => !a.is_active).length})
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Spinner /></div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={tab === "active" ? <Bell className="w-8 h-8" /> : <BellOff className="w-8 h-8" />}
          title={tab === "active" ? "// no_active_alerts" : "// no_triggered_alerts"}
          description={tab === "active" ? "Add a target price above to get notified." : "Triggered alerts will appear here."}
        />
      ) : (
        <div className="card divide-y divide-line">
          {filtered.map((a) => (
            <div key={a.id} className="flex items-center gap-3 p-4">
              <div className={`w-2 h-2 rounded-full ${a.is_active ? "bg-accent animate-pulse-glow" : "bg-ink-faint"}`} />
              <div className="font-mono font-semibold text-sm">{a.ticker}</div>
              <Pill tone={a.condition === "above" ? "up" : "down"}>{a.condition}</Pill>
              <div className="font-mono text-sm">{fmtCurrency(parseFloat(a.target_price))}</div>
              <div className="flex-1 font-mono text-[11px] text-ink-faint">
                {a.is_active
                  ? `created ${timeAgo(a.created_at)}`
                  : <>triggered {fmtDate(a.triggered_at!, "time")} @ {fmtCurrency(parseFloat(a.triggered_price || "0"))}</>
                }
              </div>
              <button onClick={() => onDelete(a.id)} className="btn-icon hover:text-down" aria-label="Delete">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
