"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Loader2, TrendingUp, TrendingDown } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader, EmptyState, Spinner } from "@/components/ui";
import { portfolio, ApiError } from "@/lib/api";
import { fmtCurrency, fmtPercent, pnlClass } from "@/lib/utils";
import type { Watchlist, Quote } from "@/types";

export default function WatchlistPage() {
  return (<AppShell><WatchlistView /></AppShell>);
}

function WatchlistView() {
  const [items, setItems]   = useState<Watchlist[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);
  const [ticker, setTicker]   = useState("");
  const [adding, setAdding]   = useState(false);
  const [error, setError]     = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await portfolio.watchlist();
      setItems(data.results);
      // Fetch quotes in parallel
      const quotesEntries = await Promise.allSettled(
        data.results.map((w) => portfolio.quote(w.ticker))
      );
      const map: Record<string, Quote> = {};
      quotesEntries.forEach((r, i) => {
        if (r.status === "fulfilled") map[data.results[i].ticker] = r.value;
      });
      setQuotes(map);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const onAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setAdding(true);
    try {
      await portfolio.addWatchlist({ ticker });
      setTicker("");
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to add");
    } finally { setAdding(false); }
  };

  const onRemove = async (id: number) => {
    try {
      await portfolio.removeWatchlist(id);
      load();
    } catch (e) { console.error(e); }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1200px] mx-auto">
      <PageHeader title="watchlist" subtitle={`${items.length} tickers being watched`} />

      {/* Add */}
      <form onSubmit={onAdd} className="flex gap-2 mb-4">
        <input type="text" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="add ticker..." className="input font-mono max-w-xs" required />
        <button type="submit" disabled={adding} className="btn-primary">
          {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          add
        </button>
      </form>
      {error && <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg mb-4">! {error}</div>}

      {loading ? (
        <div className="flex items-center justify-center h-48"><Spinner /></div>
      ) : items.length === 0 ? (
        <EmptyState
          title="// watchlist_empty"
          description="Add tickers above to track them without holding a position."
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {items.map((w) => {
            const q = quotes[w.ticker];
            const up = q && q.change_abs >= 0;
            return (
              <div key={w.id} className="card p-4 relative group">
                <button onClick={() => onRemove(w.id)}
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity btn-icon w-7 h-7 hover:text-down" aria-label="Remove">
                  <Trash2 className="w-3 h-3" />
                </button>

                <div className="font-mono font-bold text-sm mb-2">{w.ticker}</div>
                {q ? (
                  <>
                    <div className="font-mono text-xl font-medium tracking-tight">{fmtCurrency(q.price)}</div>
                    <div className={`font-mono text-xs mt-1 flex items-center gap-1 ${pnlClass(q.change_abs)}`}>
                      {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {fmtCurrency(q.change_abs, { sign: true })} ({fmtPercent(q.change_pct, { sign: true })})
                    </div>
                  </>
                ) : (
                  <div className="font-mono text-xs text-ink-faint">// no_quote</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
