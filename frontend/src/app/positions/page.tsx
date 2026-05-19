"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Search, ChevronRight } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader, Modal, Spinner, EmptyState, Pill } from "@/components/ui";
import { portfolio, ApiError } from "@/lib/api";
import { fmtCurrency, fmtPercent, pnlClass, tickerInitial } from "@/lib/utils";
import type { Position } from "@/types";

export default function PositionsPage() {
  return (<AppShell><Positions /></AppShell>);
}

function Positions() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [filter, setFilter]       = useState("");
  const [openOnly, setOpenOnly]   = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await portfolio.positions({ is_open: openOnly });
      setPositions(data.results);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load positions");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [openOnly]);

  useEffect(() => { load(); }, [load]);

  const filtered = positions.filter((p) =>
    !filter || p.ticker.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Positions"
        subtitle={`${filtered.length} ${openOnly ? "open" : "closed"} ${filtered.length === 1 ? "position" : "positions"}`}
        actions={
          <button onClick={() => setModalOpen(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> Open position
          </button>
        }
      />

      {/* Controls */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            type="text"
            placeholder="filter by ticker..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input pl-10 font-mono"
          />
        </div>
        <div className="flex bg-bg-card border border-line rounded-lg p-1">
          <button
            onClick={() => setOpenOnly(true)}
            className={`px-3 py-1.5 text-xs font-mono rounded ${openOnly ? "bg-accent/10 text-accent" : "text-ink-muted"}`}
          >open</button>
          <button
            onClick={() => setOpenOnly(false)}
            className={`px-3 py-1.5 text-xs font-mono rounded ${!openOnly ? "bg-accent/10 text-accent" : "text-ink-muted"}`}
          >closed</button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Spinner /></div>
      ) : error ? (
        <div className="card p-6 text-center">
          <p className="font-mono text-sm text-down mb-3">! {error}</p>
          <button onClick={load} className="btn-secondary text-xs">retry</button>
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No positions found"
          description={openOnly ? "Open your first position to start tracking." : "No closed positions yet."}
          action={openOnly && (
            <button onClick={() => setModalOpen(true)} className="btn-primary">
              <Plus className="w-4 h-4" /> Open position
            </button>
          )}
        />
      ) : (
        <div className="card divide-y divide-line">
          {filtered.map((pos) => {
            const hasPnl = pos.unrealized_pnl !== null;
            const pnl    = hasPnl ? parseFloat(pos.unrealized_pnl!) : null;
            const pnlPct = pos.unrealized_pnl_pct !== null ? parseFloat(pos.unrealized_pnl_pct!) : null;
            return (
              <Link
                key={pos.id}
                href={`/positions/${pos.id}`}
                className="flex items-center gap-3 p-4 hover:bg-bg-hover/40 transition-colors"
              >
                <div className={`w-11 h-11 rounded-lg flex items-center justify-center font-mono font-bold text-xs border ${
                  pnl === null       ? "bg-bg-card text-ink-muted border-line"
                  : pnl >= 0        ? "bg-up/15 text-up border-up/30"
                                    : "bg-down/15 text-down border-down/30"
                }`}>
                  {tickerInitial(pos.ticker)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-sm">{pos.ticker}</span>
                    {pos.asset_type !== "stock" && <Pill tone="cyan">{pos.asset_type}</Pill>}
                    {pos.strike && <span className="font-mono text-[11px] text-ink-muted">${pos.strike}</span>}
                    {pos.expiry && <span className="font-mono text-[11px] text-ink-faint">· {pos.expiry}</span>}
                  </div>
                  <div className="font-mono text-[11px] text-ink-muted mt-1">
                    {pos.quantity} {pos.asset_type === "stock" ? "shares" : "contracts"} @ ${parseFloat(pos.avg_cost).toFixed(2)} avg
                  </div>
                </div>
                <div className="text-right hidden sm:block flex-shrink-0">
                  <div className="font-mono font-medium text-sm">
                    {pos.current_price ? `$${parseFloat(pos.current_price).toFixed(2)}` : "—"}
                  </div>
                  <div className="font-mono text-[10px] text-ink-faint">current</div>
                </div>
                <div className="text-right flex-shrink-0 min-w-[100px]">
                  {pnl !== null ? (
                    <>
                      <div className={`font-mono font-medium text-sm ${pnlClass(pnl)}`}>
                        {fmtCurrency(pnl, { sign: true })}
                      </div>
                      <div className={`font-mono text-[11px] ${pnlClass(pnl)}`}>
                        {pnlPct !== null ? fmtPercent(pnlPct, { sign: true }) : "—"}
                      </div>
                    </>
                  ) : (
                    <div className="font-mono text-sm text-ink-faint">—</div>
                  )}
                </div>
                <ChevronRight className="w-4 h-4 text-ink-faint flex-shrink-0" />
              </Link>
            );
          })}
        </div>
      )}

      <OpenPositionModal open={modalOpen} onClose={() => setModalOpen(false)} onCreated={load} />
    </div>
  );
}

// ─── Open Position Modal ─────────────────────────────────────

function OpenPositionModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [ticker, setTicker]       = useState("");
  const [assetType, setAssetType] = useState<"stock" | "call" | "put">("stock");
  const [quantity, setQuantity]   = useState("");
  const [avgCost, setAvgCost]     = useState("");
  const [strike, setStrike]       = useState("");
  const [expiry, setExpiry]       = useState("");
  const [error, setError]   = useState("");
  const [busy, setBusy]     = useState(false);

  const reset = () => {
    setTicker(""); setAssetType("stock"); setQuantity(""); setAvgCost("");
    setStrike(""); setExpiry(""); setError("");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      const data: Parameters<typeof portfolio.createPosition>[0] = {
        ticker, asset_type: assetType, quantity, avg_cost: avgCost,
      };
      if (assetType !== "stock") {
        data.strike = strike;
        data.expiry = expiry;
      }
      await portfolio.createPosition(data);
      onCreated();
      reset();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create position");
    } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="open position" width="md">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">ticker</label>
            <input type="text" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
              required placeholder="PLTR" className="input font-mono" />
          </div>
          <div>
            <label className="label">type</label>
            <select value={assetType} onChange={(e) => setAssetType(e.target.value as "stock" | "call" | "put")} className="input">
              <option value="stock">stock</option>
              <option value="call">call</option>
              <option value="put">put</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">quantity</label>
            <input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)}
              required step="0.0001" placeholder="10" className="input font-mono" />
          </div>
          <div>
            <label className="label">avg cost</label>
            <input type="number" value={avgCost} onChange={(e) => setAvgCost(e.target.value)}
              required step="0.01" placeholder="175.50" className="input font-mono" />
          </div>
        </div>

        {assetType !== "stock" && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">strike</label>
              <input type="number" value={strike} onChange={(e) => setStrike(e.target.value)}
                required step="0.01" placeholder="160" className="input font-mono" />
            </div>
            <div>
              <label className="label">expiry</label>
              <input type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)}
                required className="input font-mono" />
            </div>
          </div>
        )}

        {error && <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">! {error}</div>}

        <div className="flex gap-2 mt-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1">cancel</button>
          <button type="submit" disabled={busy} className="btn-primary flex-1">
            {busy ? <Spinner label="" /> : <Plus className="w-4 h-4" />}
            {busy ? "creating" : "create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
