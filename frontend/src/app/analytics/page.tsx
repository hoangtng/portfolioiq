"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid, Legend,
} from "recharts";
import {
  Target, TrendingUp, TrendingDown, Award, Camera, Loader2,
} from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader, Spinner, EmptyState, Pill } from "@/components/ui";
import { analytics, ApiError } from "@/lib/api";
import { fmtCurrency, fmtPercent, pnlClass, fmtDate, tickerInitial } from "@/lib/utils";
import type {
  PnLHistoryItem, PerformanceStats, TopPerformers, AssetAllocation, RealizedSummary,
} from "@/types";

const PIE_COLORS = ["#00FFAA", "#00D4FF", "#FFAA00", "#FF3366", "#B247FF", "#FF8C00", "#5EEAD4", "#FCD34D"];

export default function AnalyticsPage() {
  return (<AppShell><Analytics /></AppShell>);
}

function Analytics() {
  const [history,    setHistory]    = useState<PnLHistoryItem[]>([]);
  const [stats,      setStats]      = useState<PerformanceStats | null>(null);
  const [performers, setPerformers] = useState<TopPerformers | null>(null);
  const [allocation, setAllocation] = useState<AssetAllocation | null>(null);
  const [realized,   setRealized]   = useState<RealizedSummary | null>(null);
  const [days, setDays]   = useState(90);
  const [loading,        setLoading]        = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error,          setError]          = useState("");
  const [snapshotBusy, setSnapshotBusy] = useState(false);
  const [snapshotMessage, setSnapshotMessage] = useState("");
  const snapshotTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const h = await analytics.history(days);
      setHistory(h.history);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load history");
    } finally {
      setHistoryLoading(false);
    }
  }, [days]);

  const loadStatic = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [s, p, a, r] = await Promise.all([
        analytics.stats(),
        analytics.performers(5),
        analytics.allocation(),
        analytics.realized(),
      ]);
      setStats(s); setPerformers(p); setAllocation(a); setRealized(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadHistory(); }, [loadHistory]);
  useEffect(() => { void loadStatic(); }, [loadStatic]);

  const takeSnapshot = async () => {
    setSnapshotBusy(true); setSnapshotMessage("");
    try {
      await analytics.snapshot();
      setSnapshotMessage("Snapshot taken");
      void loadStatic();
      void loadHistory();
    } catch (e) {
      setSnapshotMessage(e instanceof ApiError ? `error: ${e.message}` : "Snapshot failed");
    } finally {
      setSnapshotBusy(false);
      if (snapshotTimerRef.current) clearTimeout(snapshotTimerRef.current);
      snapshotTimerRef.current = setTimeout(() => setSnapshotMessage(""), 4000);
    }
  };

  if (loading && !stats) {
    return (<div className="p-8 flex items-center justify-center"><Spinner /></div>);
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Analytics"
        subtitle="P&L history · Win rate · Allocation · Realized summary"
        actions={
          <button onClick={takeSnapshot} disabled={snapshotBusy} className="btn-secondary">
            {snapshotBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Camera className="w-4 h-4" />}
            <span className="hidden sm:inline">Snapshot</span>
          </button>
        }
      />

      {snapshotMessage && (
        <div className="font-mono text-xs text-accent mb-4"> {snapshotMessage}</div>
      )}
      {error && (
        <div className="font-mono text-xs text-down mb-4 px-3 py-2 rounded border border-down/30 bg-down/10">
          {error}
        </div>
      )}

      {/* Performance stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <div className="stat-card">
            <div className="stat-label"><Target className="w-3.5 h-3.5" /> Win rate</div>
            <div className="stat-value">{stats.win_rate.toFixed(1)}%</div>
            <div className="stat-delta text-ink-muted">{stats.win_count} / {stats.total_trades} Trades</div>
          </div>
          <div className="stat-card">
            <div className="stat-label"><Award className="w-3.5 h-3.5" /> profit factor</div>
            <div className="stat-value">{stats.profit_factor !== null ? stats.profit_factor.toFixed(2) : "—"}</div>
            <div className="stat-delta text-ink-muted">Gross profit / loss</div>
          </div>
          <div className="stat-card">
            <div className="stat-label"><TrendingUp className="w-3.5 h-3.5" /> Total p&l</div>
            <div className={`stat-value ${pnlClass(stats.total_pnl)}`}>{fmtCurrency(stats.total_pnl, { sign: true })}</div>
            <div className="stat-delta text-ink-muted">
              Realized {fmtCurrency(stats.total_realized_pnl, { sign: true, compact: true })}
              {" · "}
              Unrealized {fmtCurrency(stats.total_unrealized_pnl, { sign: true, compact: true })}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label"><TrendingUp className="w-3.5 h-3.5" /> avg trade</div>
            <div className="stat-value text-sm leading-tight">
              <span className="text-up">{fmtCurrency(stats.avg_win, { sign: true })}</span>
              <br/>
              <span className="text-down">{fmtCurrency(stats.avg_loss, { sign: true })}</span>
            </div>
            <div className="stat-delta text-ink-muted">Avg win / loss</div>
          </div>
        </div>
      )}

      {/* Chart + allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4 mb-6">
        <div className="card p-4 sm:p-5">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h3 className="section-title flex items-center gap-2">
               P&L history
              {historyLoading && <Loader2 className="w-3.5 h-3.5 animate-spin text-ink-muted" />}
            </h3>
            <div className="flex bg-bg-deepest border border-line rounded-lg p-1">
              {[30, 90, 180].map((d) => (
                <button key={d} onClick={() => setDays(d)}
                  className={`px-3 py-1 text-[11px] font-mono rounded ${days === d ? "bg-accent/10 text-accent" : "text-ink-muted"}`}>
                  {d}d
                </button>
              ))}
            </div>
          </div>

          {history.length === 0 ? (
            <div className="h-[280px] flex items-center justify-center text-center px-6">
              <div>
                <div className="font-mono text-sm text-ink-muted mb-2"> No snapshots yet</div>
                <p className="text-xs text-ink-faint">
                  Daily snapshots run Mon-Fri at 21:00 UTC. Take one manually with the button above.
                </p>
              </div>
            </div>
          ) : (
            <div className="h-[280px] -ml-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history} margin={{ top: 5, right: 8, left: 0, bottom: 5 }}>
                  <defs>
                    <linearGradient id="histGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00FFAA" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#00FFAA" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis
                    dataKey="date"
                    stroke="rgba(255,255,255,0.3)"
                    fontSize={10}
                    tickFormatter={(d: string) => new Date(d + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    tick={{ fontFamily: "JetBrains Mono" }}
                  />
                  <YAxis
                    stroke="rgba(255,255,255,0.3)"
                    fontSize={10}
                    tickFormatter={(v: number) => Math.abs(v) >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`}
                    tick={{ fontFamily: "JetBrains Mono" }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0E141B",
                      border: "1px solid rgba(0,255,170,0.2)",
                      borderRadius: "8px",
                      fontFamily: "JetBrains Mono",
                      fontSize: "12px",
                    }}
                    labelStyle={{ color: "#00FFAA" }}
                    formatter={(v: number) => [`$${v.toLocaleString()}`, "value"]}
                  />
                  <Area type="monotone" dataKey="total_market_value" stroke="#00FFAA"
                    strokeWidth={2} fill="url(#histGradient)" dot={false}
                    activeDot={{ r: 5, fill: "#00FFAA", stroke: "#0A0E14", strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Allocation pie */}
        <div className="card p-4 sm:p-5">
          <h3 className="section-title mb-4"> Allocation by ticker</h3>
          {!allocation || allocation.by_ticker.length === 0 ? (
            <div className="h-[280px] flex items-center justify-center font-mono text-xs text-ink-muted">
               No positions
            </div>
          ) : (
            <>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={allocation.by_ticker}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      stroke="#0E141B"
                      strokeWidth={2}
                    >
                      {allocation.by_ticker.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0E141B",
                        border: "1px solid rgba(0,255,170,0.2)",
                        borderRadius: "8px",
                        fontFamily: "JetBrains Mono",
                        fontSize: "12px",
                      }}
                      formatter={(v: number, _name, item) => [
                        `$${v.toLocaleString()} (${item.payload.pct}%)`,
                        item.payload.name,
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-1.5 mt-3">
                {allocation.by_ticker.slice(0, 6).map((item, i) => (
                  <div key={item.name} className="flex items-center justify-between gap-2 text-[11px] font-mono">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span className="font-semibold truncate">{item.name}</span>
                    </div>
                    <span className="text-ink-muted flex-shrink-0">{item.pct}%</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Top performers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="card p-4 sm:p-5">
          <h3 className="section-title mb-4 flex items-center gap-2">
            <TrendingUp className="w-3.5 h-3.5" />  Top winners
          </h3>
          {!performers || performers.best.length === 0 ? (
            <div className="font-mono text-xs text-ink-muted py-8 text-center"> No data</div>
          ) : (
            <div className="flex flex-col">
              {performers.best.map((p) => (
                <div key={p.id} className="flex items-center gap-3 py-2.5 border-t border-line first:border-t-0">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center font-mono font-bold text-[11px] bg-up/15 text-up border border-up/30">
                    {tickerInitial(p.ticker)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-mono font-semibold text-sm">
                      {p.ticker}
                      {p.asset_type !== "stock" && <Pill tone="cyan" className="ml-1.5">{p.asset_type}</Pill>}
                    </div>
                    <div className="font-mono text-[10px] text-ink-faint">
                      {fmtCurrency(p.market_value, { compact: true })} value
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono font-medium text-sm text-up">{fmtCurrency(p.pnl, { sign: true })}</div>
                    <div className="font-mono text-[10px] text-up">{fmtPercent(p.pnl_pct, { sign: true })}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card p-4 sm:p-5">
          <h3 className="section-title mb-4 flex items-center gap-2">
            <TrendingDown className="w-3.5 h-3.5" />  Top losers
          </h3>
          {!performers ? (
            <div className="font-mono text-xs text-ink-muted py-8 text-center"> No data</div>
          ) : performers.worst.length === 0 ? (
            <div className="font-mono text-xs text-ink-muted py-8 text-center"> All positions green</div>
          ) : (
            <div className="flex flex-col">
              {performers.worst.map((p) => (
                <div key={p.id} className="flex items-center gap-3 py-2.5 border-t border-line first:border-t-0">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center font-mono font-bold text-[11px] bg-down/15 text-down border border-down/30">
                    {tickerInitial(p.ticker)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-mono font-semibold text-sm">
                      {p.ticker}
                      {p.asset_type !== "stock" && <Pill tone="cyan" className="ml-1.5">{p.asset_type}</Pill>}
                    </div>
                    <div className="font-mono text-[10px] text-ink-faint">
                      {fmtCurrency(p.market_value, { compact: true })} value
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono font-medium text-sm text-down">{fmtCurrency(p.pnl, { sign: true })}</div>
                    <div className="font-mono text-[10px] text-down">{fmtPercent(p.pnl_pct, { sign: true })}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Realized P&L by month */}
      {realized && realized.by_month.length > 0 && (
        <div className="card p-4 sm:p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="section-title"> Realized p&l by month</h3>
            <div className={`font-mono text-sm font-medium ${pnlClass(realized.total_realized_pnl)}`}>
              Total {fmtCurrency(realized.total_realized_pnl, { sign: true })}
            </div>
          </div>
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={realized.by_month} margin={{ top: 5, right: 8, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="month" stroke="rgba(255,255,255,0.3)" fontSize={10}
                  tick={{ fontFamily: "JetBrains Mono" }} />
                <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10}
                  tickFormatter={(v: number) => Math.abs(v) >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`}
                  tick={{ fontFamily: "JetBrains Mono" }} />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  contentStyle={{
                    backgroundColor: "#0E141B",
                    border: "1px solid rgba(0,255,170,0.2)",
                    borderRadius: "8px",
                    fontFamily: "JetBrains Mono",
                    fontSize: "12px",
                  }}
                  labelStyle={{ color: "#00FFAA" }}
                  formatter={(v: number) => [fmtCurrency(v, { sign: true }), "realized"]}
                />
                <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                  {realized.by_month.map((m, i) => (
                    <Cell key={i} fill={m.pnl >= 0 ? "#00FFAA" : "#FF3366"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Realized P&L by ticker */}
      {realized && realized.by_ticker.length > 0 && (
        <div className="card">
          <div className="px-5 py-4 border-b border-line">
            <h3 className="section-title"> Realized p&l by ticker</h3>
          </div>
          <div className="divide-y divide-line">
            {realized.by_ticker.map((t) => (
              <div key={t.ticker} className="flex items-center gap-3 p-4">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center font-mono font-bold text-[11px] border ${
                  t.pnl >= 0 ? "bg-up/15 text-up border-up/30" : "bg-down/15 text-down border-down/30"
                }`}>
                  {tickerInitial(t.ticker)}
                </div>
                <div className="font-mono font-semibold text-sm flex-1">{t.ticker}</div>
                <div className={`font-mono font-medium text-sm ${pnlClass(t.pnl)}`}>
                  {fmtCurrency(t.pnl, { sign: true })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {(!stats || stats.total_trades === 0) && history.length === 0 && (
        <EmptyState
          title=" analytics_warming_up"
          description="Close a few trades and take daily snapshots to see your performance metrics populate."
        />
      )}
    </div>
  );
}
