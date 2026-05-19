"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Wallet, TrendingUp, Target, Activity, ArrowRight,
  Search, Bell, Settings, ArrowUpRight, ArrowDownRight, X,
} from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PnLChart } from "@/components/charts/PnLChart";
import { PageHeader, StatCard, Spinner, Pill, Modal } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { portfolio, analytics } from "@/lib/api";
import { fmtCurrency, fmtPercent, pnlClass, tickerInitial, getMarketStatus } from "@/lib/utils";
import type { PortfolioSummary, PnLHistoryItem } from "@/types";
import { useValueFlash } from "@/lib/use-value-flash";

export default function DashboardPage() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}

function Dashboard() {
  const { user } = useAuth();
  const router = useRouter();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [history, setHistory] = useState<PnLHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [market, setMarket] = useState(() => getMarketStatus());
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [recentAlerts, setRecentAlerts] = useState<import("@/types").PriceAlert[]>([]);
  const [alertsDismissed, setAlertsDismissed] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [s, h] = await Promise.all([
          portfolio.summary(),
          analytics.history(30),
        ]);
        setSummary(s);
        setHistory(h.history);
        const id = setInterval(() => setMarket(getMarketStatus()), 30_000);
        return () => clearInterval(id);
      } catch (e) {
        console.error("Failed to load dashboard:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Alerts fetch is independent — failure must not block the main dashboard
  useEffect(() => {
    (async () => {
      try {
        const alertsRes = await portfolio.alerts();
        const cutoff = Date.now() - 24 * 60 * 60 * 1000;
        const recent = alertsRes.results.filter(
          (a) => !a.is_active && a.triggered_at && new Date(a.triggered_at).getTime() > cutoff,
        );
        setRecentAlerts(recent);
      } catch (e) {
        console.error("Failed to load alerts:", e);
      }
    })();
  }, []);

  // Cmd+K / Ctrl+K opens search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Focus input when modal opens
  useEffect(() => {
    if (searchOpen) {
      setSearchQuery("");
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [searchOpen]);

  const totalValue   = summary ? parseFloat(summary.total_market_value)        : 0;
  const totalPnl     = summary ? parseFloat(summary.total_unrealized_pnl)      : 0;
  const totalPnlPct  = summary ? parseFloat(summary.total_unrealized_pnl_pct)  : 0;
  const positions    = summary?.positions ?? [];
  const searchResults = searchQuery.trim()
    ? positions.filter((p) =>
        p.ticker.toLowerCase().includes(searchQuery.trim().toLowerCase()),
      )
    : positions.slice(0, 8);
  const positivePnl  = totalPnl >= 0;
  // Today's change = current value − most recent snapshot BEFORE today.
  const todayStr = new Date().toISOString().slice(0, 10);
  const previousSnapshot = history.length
    ? [...history].reverse().find((h) => String(h.date) !== todayStr)
    : undefined;
  const previousValue = previousSnapshot
    ? Number(previousSnapshot.total_market_value)
    : null;
  const todayChange     = previousValue !== null ? totalValue - previousValue : null;
  const todayChangePct  = previousValue && previousValue !== 0
    ? (todayChange! / previousValue) * 100
    : null;

  const todayChangeFlash = useValueFlash(todayChange);

  // Sort positions by absolute P&L for the "top positions" panel
  const topPositions = [...positions]
    .filter((p) => p.unrealized_pnl !== null)
    .sort((a, b) =>
      Math.abs(parseFloat(b.unrealized_pnl!)) - Math.abs(parseFloat(a.unrealized_pnl!)),
    )
    .slice(0, 5);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <h1 className="font-mono font-bold text-xl sm:text-2xl">
            <span className="text-accent">{">"}</span> {user?.first_name?.toLowerCase() || user?.email?.split("@")[0]}<span className="cursor-blink"></span>
          </h1>
          <p className="font-mono text-xs text-ink-muted mt-1">

            {new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}
            {" · "}
            <span className={
                market.state === "Open"        ? "text-up"      :
                market.state === "Pre Market"  ? "text-warn"    :
                market.state === "After Hours" ? "text-warn"    :
                                                "text-down"
            }>
                Market {market.state}
            </span>
            <span className="text-ink-faint"> · {market.nyTime} NY</span>
          </p>
          
        </div>
        <div className="flex gap-2">
          <button className="btn-icon" aria-label="Search" onClick={() => setSearchOpen(true)}>
            <Search className="w-4 h-4" />
          </button>
          <Link href="/alerts" className="btn-icon relative" aria-label="Alerts">
            <Bell className="w-4 h-4" />
            {recentAlerts.length > 0 && !alertsDismissed && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-down border-2 border-bg-card animate-pulse" />
            )}
          </Link>
          <Link href="/settings" className="btn-icon" aria-label="Settings">
            <Settings className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Spinner label="loading portfolio data" />
        </div>
      ) : (
        <>
          {/* Triggered alerts banner */}
          {recentAlerts.length > 0 && !alertsDismissed && (
            <div className="mb-4 flex items-center gap-3 px-4 py-3 rounded-lg border border-warn/40 bg-warn/10">
              <Bell className="w-3.5 h-3.5 text-warn flex-shrink-0" />
              <div className="flex-1 font-mono text-xs text-warn">
                {recentAlerts.length === 1
                  ? <>Alert fired: <span className="font-semibold">{recentAlerts[0].ticker}</span> hit ${parseFloat(recentAlerts[0].triggered_price ?? "0").toFixed(2)}</>
                  : <><span className="font-semibold">{recentAlerts.length} alerts</span> triggered in the last 24h</>
                }
              </div>
              <Link href="/alerts?tab=triggered" className="font-mono text-[11px] text-warn underline underline-offset-2 flex-shrink-0">
                view →
              </Link>
              <button onClick={() => setAlertsDismissed(true)} className="btn-icon w-6 h-6 flex-shrink-0" aria-label="Dismiss">
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Summary cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <StatCard
              featured
              icon={<Wallet className="w-3.5 h-3.5" />}
              label="portfolio"
              value={fmtCurrency(totalValue)}
              delta={
                <span className={pnlClass(totalPnl)}>
                  {positivePnl ? <ArrowUpRight className="w-3 h-3 inline" /> : <ArrowDownRight className="w-3 h-3 inline" />}
                  {" "}{fmtCurrency(totalPnl, { sign: true })} ({fmtPercent(totalPnlPct, { sign: true })})
                </span>
              }
            />
            <StatCard
              icon={<Activity className="w-3.5 h-3.5" />}
              label="today's change"
              value={
                todayChange !== null
                  ? <span className={todayChangeFlash}>{fmtCurrency(todayChange, { sign: true })}</span>
                  : "—"
              }
              delta={
                todayChangePct !== null
                  ? <span className={pnlClass(todayChange ?? 0)}>
                      {fmtPercent(todayChangePct, { sign: true })} vs yesterday
                    </span>
                  : <span className="text-ink-faint">awaiting snapshots</span>
              }
            />
            <StatCard
              icon={<TrendingUp className="w-3.5 h-3.5" />}
              label="open positions"
              value={summary?.positions_count ?? 0}
              delta={<span className="text-ink-muted">
                {fmtCurrency(parseFloat(summary?.total_cost_basis || "0"), { compact: true })} invested
              </span>}
            />
            <StatCard
              icon={<Target className="w-3.5 h-3.5" />}
              label="cost basis"
              value={fmtCurrency(parseFloat(summary?.total_cost_basis || "0"), { compact: true })}
              delta={<span className="text-ink-muted">total deployed</span>}
            />
            
          </div>

          {/* Two columns: chart + top positions */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">

            {/* P&L Chart */}
            <div className="card p-4 sm:p-5">
              <div className="flex items-center justify-between mb-1">
                <h3 className="section-title">p&l history</h3>
                <Link href="/analytics" className="font-mono text-[11px] text-ink-muted hover:text-accent flex items-center gap-1">
                  View all <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
              <PnLChart
                history={history}
                summary={summary}
                loading={!summary && history.length === 0}
              />
            </div>

            {/* Top positions */}
            <div className="card p-4 sm:p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="section-title">top positions</h3>
                <Link href="/positions" className="font-mono text-[11px] text-ink-muted hover:text-accent flex items-center gap-1">
                  view all <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {topPositions.length === 0 ? (
                <div className="text-center py-10">
                  <div className="font-mono text-sm text-ink-muted mb-2">No positions</div>
                  <Link href="/positions" className="font-mono text-xs text-accent hover:underline">
                    open your first position →
                  </Link>
                </div>
              ) : (
                <div className="flex flex-col">
                  {topPositions.map((pos) => {
                    const pnl    = pos.unrealized_pnl ? parseFloat(pos.unrealized_pnl) : 0;
                    const pnlPct = pos.unrealized_pnl_pct ? parseFloat(pos.unrealized_pnl_pct) : 0;
                    return (
                      <Link
                        key={pos.id}
                        href={`/positions/${pos.id}`}
                        className="flex items-center gap-3 py-3 border-t border-line first:border-t-0 hover:bg-bg-hover/40 -mx-2 px-2 rounded-lg transition-colors"
                      >
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-mono font-bold text-[11px] border ${
                          pnl >= 0 ? "bg-up/15 text-up border-up/30" : "bg-down/15 text-down border-down/30"
                        }`}>
                          {tickerInitial(pos.ticker)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-mono font-semibold text-sm truncate">
                            {pos.ticker}
                            {pos.asset_type !== "stock" && (
                              <Pill tone="cyan" className="ml-1.5">{pos.asset_type}</Pill>
                            )}
                          </div>
                          <div className="font-mono text-[10px] text-ink-faint mt-0.5">
                            {pos.quantity} @ ${parseFloat(pos.avg_cost).toFixed(2)}
                          </div>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="font-mono font-medium text-sm">
                            {pos.current_price ? `$${parseFloat(pos.current_price).toFixed(2)}` : "—"}
                          </div>
                          <div className={`font-mono text-[11px] mt-0.5 ${pnlClass(pnl)}`}>
                            {fmtCurrency(pnl, { sign: true })} · {fmtPercent(pnlPct, { sign: true })}
                          </div>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Search modal */}
      <Modal open={searchOpen} onClose={() => setSearchOpen(false)} title="search positions" width="md">
        <div className="flex flex-col gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-muted pointer-events-none" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="ticker…"
              className="input w-full pl-8 font-mono text-sm"
            />
          </div>

          {searchResults.length === 0 ? (
            <p className="font-mono text-xs text-ink-muted text-center py-6">
              {positions.length === 0 ? "No open positions" : "No matches"}
            </p>
          ) : (
            <div className="flex flex-col max-h-72 overflow-y-auto -mx-1">
              {searchResults.map((pos) => {
                const pnl    = pos.unrealized_pnl ? parseFloat(pos.unrealized_pnl) : 0;
                const pnlPct = pos.unrealized_pnl_pct ? parseFloat(pos.unrealized_pnl_pct) : 0;
                return (
                  <button
                    key={pos.id}
                    onClick={() => { setSearchOpen(false); router.push(`/positions/${pos.id}`); }}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-bg-hover/50 text-left transition-colors"
                  >
                    <div className={`w-8 h-8 rounded-md flex items-center justify-center font-mono font-bold text-[10px] border flex-shrink-0 ${
                      pnl >= 0 ? "bg-up/15 text-up border-up/30" : "bg-down/15 text-down border-down/30"
                    }`}>
                      {tickerInitial(pos.ticker)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-mono text-sm font-semibold">
                        {pos.ticker}
                        {pos.asset_type !== "stock" && (
                          <Pill tone="cyan" className="ml-1.5">{pos.asset_type}</Pill>
                        )}
                      </div>
                      <div className="font-mono text-[10px] text-ink-faint">{pos.quantity} shares</div>
                    </div>
                    <div className={`font-mono text-xs flex-shrink-0 ${pnlClass(pnl)}`}>
                      {fmtCurrency(pnl, { sign: true })}
                      <span className="text-ink-faint ml-1">({fmtPercent(pnlPct, { sign: true })})</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          <p className="font-mono text-[10px] text-ink-faint text-right">
            ⌘K to open · Esc to close
          </p>
        </div>
      </Modal>
    </div>
  );
}
