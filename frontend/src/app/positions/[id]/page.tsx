"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, Trash2, Loader2 } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Modal, Spinner, Pill } from "@/components/ui";
import { portfolio, ApiError } from "@/lib/api";
import { fmtCurrency, fmtPercent, pnlClass, fmtDate, daysUntil } from "@/lib/utils";
import type { Position } from "@/types";

export default function PositionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (<AppShell><Detail id={parseInt(id, 10)} /></AppShell>);
}

function Detail({ id }: { id: number }) {
  const router = useRouter();
  const [pos, setPos]                     = useState<Position | null>(null);
  const [loading, setLoading]             = useState(true);
  const [tradeModalOpen, setTradeModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting]           = useState(false);

  const load = async () => {
    try {
      const data = await portfolio.position(id);
      setPos(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const onDelete = async () => {
    setDeleting(true);
    try {
      await portfolio.deletePosition(id);
      router.push("/positions");
    } catch (e) { console.error(e); }
    finally { setDeleting(false); }
  };

  if (loading) return <div className="p-8 flex items-center justify-center"><Spinner /></div>;
  if (!pos) return <div className="p-8 font-mono text-down">Position not found</div>;

  const hasPnl  = pos.unrealized_pnl !== null;
  const pnl     = hasPnl ? parseFloat(pos.unrealized_pnl!) : null;
  const pnlPct  = pos.unrealized_pnl_pct !== null ? parseFloat(pos.unrealized_pnl_pct!) : null;
  const mktVal  = pos.market_value ? parseFloat(pos.market_value) : null;
  const dte     = pos.expiry ? daysUntil(pos.expiry) : null;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1100px] mx-auto">
      <Link href="/positions" className="inline-flex items-center gap-2 font-mono text-xs text-ink-muted hover:text-accent mb-4">
        <ArrowLeft className="w-4 h-4" /> back to positions
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div>
          <h1 className="font-mono font-bold text-2xl sm:text-3xl">
            <span className="text-accent">{">"}</span> {pos.ticker}
          </h1>
          <div className="font-mono text-xs text-ink-muted mt-1 flex items-center gap-2 flex-wrap">
            <Pill tone={pos.is_open ? "up" : "neutral"}>{pos.is_open ? "open" : "closed"}</Pill>
            <Pill tone="cyan">{pos.asset_type}</Pill>
            {pos.strike && <span>strike ${pos.strike}</span>}
            {pos.expiry && (
              <span>exp {pos.expiry} {dte !== null && (
                <span className={dte < 30 ? "text-warn" : ""}>({dte}d)</span>
              )}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {pos.is_open && (
            <button onClick={() => setTradeModalOpen(true)} className="btn-primary">
              <Plus className="w-4 h-4" /> record trade
            </button>
          )}
          <button
            onClick={() => setDeleteModalOpen(true)}
            disabled={deleting}
            className="btn-icon hover:text-down hover:border-down/30"
            aria-label="Delete"
          >
            {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <div className="stat-card">
          <div className="stat-label">current</div>
          <div className="stat-value">{pos.current_price ? `$${parseFloat(pos.current_price).toFixed(2)}` : "—"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">avg cost</div>
          <div className="stat-value">${parseFloat(pos.avg_cost).toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">market value</div>
          <div className="stat-value">{mktVal !== null ? fmtCurrency(mktVal) : "—"}</div>
          <div className="stat-delta text-ink-muted">basis {fmtCurrency(parseFloat(pos.cost_basis))}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">unrealized p&l</div>
          {pnl !== null ? (
            <>
              <div className={`stat-value ${pnlClass(pnl)}`}>{fmtCurrency(pnl, { sign: true })}</div>
              <div className={`stat-delta ${pnlClass(pnl)}`}>{pnlPct !== null ? fmtPercent(pnlPct, { sign: true }) : "—"}</div>
            </>
          ) : (
            <div className="stat-value text-ink-faint">—</div>
          )}
        </div>
      </div>

      {/* Trade history */}
      <div className="card">
        <div className="px-5 py-4 border-b border-line">
          <h3 className="section-title">Trade history ({pos.trades.length})</h3>
        </div>
        {pos.trades.length === 0 ? (
          <div className="p-10 text-center font-mono text-sm text-ink-muted">No trades yet</div>
        ) : (
          <div className="divide-y divide-line">
            {pos.trades.map((t) => {
              const rPnl = t.realized_pnl ? parseFloat(t.realized_pnl) : null;
              const fees = parseFloat(t.fees);
              return (
                <div key={t.id} className="px-5 py-3 flex items-center gap-4 flex-wrap">
                  <Pill tone={t.side === "buy" ? "up" : "down"}>{t.side}</Pill>
                  <div className="font-mono text-xs text-ink-dim">
                    {t.quantity} @ <span className="text-ink">${parseFloat(t.price).toFixed(2)}</span>
                  </div>
                  <div className="font-mono text-xs text-ink-faint flex-1">
                    {fmtDate(t.executed_at, "time")}
                  </div>
                  {fees > 0 && (
                    <div className="font-mono text-xs text-ink-muted">
                      fees {fmtCurrency(fees)}
                    </div>
                  )}
                  {rPnl !== null && (
                    <div className={`font-mono text-xs font-medium ${pnlClass(rPnl)}`}>
                      realized {fmtCurrency(rPnl, { sign: true })}
                    </div>
                  )}
                  <div className="font-mono text-xs text-ink-muted">
                    {fmtCurrency(parseFloat(t.total_value))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <RecordTradeModal
        open={tradeModalOpen}
        onClose={() => setTradeModalOpen(false)}
        positionId={id}
        onSaved={load}
      />

      <DeleteConfirmModal
        open={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={onDelete}
        ticker={pos.ticker}
        deleting={deleting}
      />
    </div>
  );
}

// ─── Record Trade Modal ───────────────────────────────────────

function RecordTradeModal({ open, onClose, positionId, onSaved }: {
  open: boolean; onClose: () => void; positionId: number; onSaved: () => void;
}) {
  const [side, setSide]         = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice]       = useState("");
  const [executed, setExecuted] = useState("");
  const [fees, setFees]         = useState("0");
  const [notes, setNotes]       = useState("");
  const [error, setError]       = useState("");
  const [busy, setBusy]         = useState(false);

  // Reset all fields when modal opens or closes
  useEffect(() => {
    if (!open) {
      setSide("buy"); setQuantity(""); setPrice("");
      setExecuted(new Date().toISOString().slice(0, 16));
      setFees("0"); setNotes(""); setError("");
    } else {
      setExecuted(new Date().toISOString().slice(0, 16));
    }
  }, [open]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await portfolio.recordTrade(positionId, {
        side, quantity, price, fees,
        executed_at: new Date(executed).toISOString(),
        notes,
      });
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to record trade");
    } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="record trade">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="flex bg-bg-deepest border border-line rounded-lg p-1">
          {(["buy", "sell"] as const).map((s) => (
            <button key={s} type="button" onClick={() => setSide(s)}
              className={`flex-1 py-2 text-xs font-mono uppercase rounded ${
                side === s ? (s === "buy" ? "bg-up/15 text-up" : "bg-down/15 text-down") : "text-ink-muted"
              }`}>{s}</button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">quantity</label>
            <input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)}
              required step="0.0001" className="input font-mono" />
          </div>
          <div>
            <label className="label">price</label>
            <input type="number" value={price} onChange={(e) => setPrice(e.target.value)}
              required step="0.01" className="input font-mono" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">executed at</label>
            <input type="datetime-local" value={executed} onChange={(e) => setExecuted(e.target.value)} className="input font-mono" />
          </div>
          <div>
            <label className="label">fees</label>
            <input type="number" value={fees} onChange={(e) => setFees(e.target.value)} step="0.01" className="input font-mono" />
          </div>
        </div>

        <div>
          <label className="label">notes</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)}
            placeholder="optional notes about this trade" rows={2} className="input resize-none" />
        </div>

        {error && <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">! {error}</div>}

        <div className="flex gap-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1">cancel</button>
          <button type="submit" disabled={busy} className="btn-primary flex-1">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {busy ? "saving" : "record"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ─── Delete Confirm Modal ─────────────────────────────────────

function DeleteConfirmModal({ open, onClose, onConfirm, ticker, deleting }: {
  open: boolean; onClose: () => void; onConfirm: () => void; ticker: string; deleting: boolean;
}) {
  return (
    <Modal open={open} onClose={onClose} title="delete position">
      <div className="flex flex-col gap-5">
        <p className="font-mono text-sm text-ink-muted">
          Delete <span className="text-ink font-semibold">{ticker}</span> and all its trades?
          This cannot be undone.
        </p>
        <div className="flex gap-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1">cancel</button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={deleting}
            className="flex-1 px-4 py-2 rounded-lg font-mono text-sm bg-down/15 text-down border border-down/30 hover:bg-down/25 transition-colors disabled:opacity-50"
          >
            {deleting ? <Loader2 className="w-4 h-4 animate-spin inline mr-1" /> : null}
            {deleting ? "deleting…" : "delete"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
