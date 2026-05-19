"use client";

import { useEffect, useState, useMemo, use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Spinner, EmptyState, Pill } from "@/components/ui";
import { portfolio } from "@/lib/api";
import { fmtCurrency, fmtNumber, fmtPercent, daysUntil } from "@/lib/utils";
import type { OptionContract, OptionsChainResponse } from "@/types";

export default function OptionsChainPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = use(params);
  return (<AppShell><Chain ticker={ticker.toUpperCase()} /></AppShell>);
}

function Chain({ ticker }: { ticker: string }) {
  const [chain, setChain] = useState<OptionsChainResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [type, setType] = useState<"call" | "put">("call");
  const [expiry, setExpiry] = useState<string>("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await portfolio.optionsChain(ticker, { type, limit: 250 });
        setChain(data);
        // Auto-select nearest expiry
        if (!expiry && data.contracts.length > 0) {
          const expiries = [...new Set(data.contracts.map((c) => c.expiry))].sort();
          if (expiries[0]) setExpiry(expiries[0]);
        }
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, [ticker, type]);

  const expiries = useMemo(() => {
    if (!chain) return [];
    return [...new Set(chain.contracts.map((c) => c.expiry))].sort();
  }, [chain]);

  const filtered = useMemo(() => {
    if (!chain) return [];
    return chain.contracts.filter((c) => !expiry || c.expiry === expiry);
  }, [chain, expiry]);

  const underlying = chain?.contracts[0]?.underlying_price;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1400px] mx-auto">
      <Link href="/options" className="inline-flex items-center gap-2 font-mono text-xs text-ink-muted hover:text-accent mb-4">
        <ArrowLeft className="w-4 h-4" /> back to search
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div>
          <h1 className="font-mono font-bold text-2xl sm:text-3xl">
            <span className="text-accent">{">"}</span> {ticker}
          </h1>
          {underlying && (
            <p className="font-mono text-xs text-ink-muted mt-1">
               Underlying: <span className="text-ink">${underlying.toFixed(2)}</span>
              {chain?.from_cache && <span className="text-ink-faint ml-2">· cached</span>}
            </p>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <div className="flex bg-bg-card border border-line rounded-lg p-1">
          {(["call", "put"] as const).map((t) => (
            <button key={t} onClick={() => setType(t)}
              className={`px-4 py-1.5 text-xs font-mono uppercase rounded ${type === t ? "bg-accent/10 text-accent" : "text-ink-muted"}`}>
              {t}s
            </button>
          ))}
        </div>

        {expiries.length > 0 && (
          <select value={expiry} onChange={(e) => setExpiry(e.target.value)}
            className="input font-mono text-xs py-2 w-auto min-w-[160px]">
            {expiries.map((d) => {
              const dte = daysUntil(d);
              return <option key={d} value={d}>{d} ({dte}d)</option>;
            })}
          </select>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Spinner /></div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No contracts found"
          description="Options data requires Massive API Options Starter plan or higher. Free tier returns empty results."
        />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead className="bg-bg-deepest border-b border-line text-ink-faint">
              <tr>
                <th className="text-left p-3 font-medium uppercase tracking-wider">strike</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider">last</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider">vol</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider">oi</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider">iv</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider">Δ</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider hidden sm:table-cell">Γ</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider hidden sm:table-cell">Θ</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider hidden md:table-cell">V</th>
                <th className="text-right p-3 font-medium uppercase tracking-wider hidden lg:table-cell">b/e</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => {
                const isITM = type === "call"
                  ? (underlying ?? 0) > c.strike
                  : (underlying ?? 0) < c.strike;
                return (
                  <tr key={c.ticker} className={`border-b border-line/50 hover:bg-bg-hover/30 ${isITM ? "bg-accent/[0.02]" : ""}`}>
                    <td className="p-3">
                      <span className={`font-semibold ${isITM ? "text-accent" : ""}`}>${c.strike}</span>
                      {isITM && <Pill tone="accent" className="ml-2">ITM</Pill>}
                    </td>
                    <td className="p-3 text-right">${c.last_price.toFixed(2)}</td>
                    <td className="p-3 text-right text-ink-dim">{c.volume.toLocaleString()}</td>
                    <td className="p-3 text-right text-ink-dim">{c.open_interest.toLocaleString()}</td>
                    <td className="p-3 text-right">{(c.iv * 100).toFixed(0)}%</td>
                    <td className="p-3 text-right">{c.delta.toFixed(3)}</td>
                    <td className="p-3 text-right text-ink-dim hidden sm:table-cell">{c.gamma.toFixed(3)}</td>
                    <td className="p-3 text-right text-ink-dim hidden sm:table-cell">{c.theta.toFixed(3)}</td>
                    <td className="p-3 text-right text-ink-dim hidden md:table-cell">{c.vega.toFixed(3)}</td>
                    <td className="p-3 text-right text-ink-dim hidden lg:table-cell">${c.break_even.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
