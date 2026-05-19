"use client";

import { useState, useMemo } from "react";
import { fmtCurrency, fmtPercent, pnlClass } from "@/lib/utils";

// ─── Types ─────────────────────────────────────────────────────────

interface HistoryItem {
  date: string | Date;
  total_market_value: number | string;
  total_unrealized_pnl: number | string;
  total_unrealized_pnl_pct: number | string;
}

interface Summary {
  total_market_value: number | string;
  total_unrealized_pnl: number | string;
  total_unrealized_pnl_pct: number | string;
}

interface Props {
  history: HistoryItem[];
  summary: Summary | null;
  loading?: boolean;
}

type Mode  = "value" | "pnl";
type Range = 7 | 30 | 90;

interface ChartPoint {
  date:        string;
  value:       number;
  marketValue: number;
  pnl:         number;
  pnl_pct:     number;
  live:        boolean;
}

// ─── Constants ─────────────────────────────────────────────────────

const VIEW_W = 1000;
const VIEW_H = 280;
const PAD    = { top: 20, right: 24, bottom: 30, left: 72 };

// ─── Component ─────────────────────────────────────────────────────

export function PnLChart({ history, summary, loading }: Props) {
  const [mode,     setMode]     = useState<Mode>("value");
  const [range,    setRange]    = useState<Range>(30);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const points = useMemo<ChartPoint[]>(() => {
    const today = new Date().toISOString().slice(0, 10);

    const historical = history
      .filter((h) => String(h.date).slice(0, 10) !== today)
      .map((h) => ({
        date:        String(h.date).slice(0, 10),
        marketValue: Number(h.total_market_value),
        pnl:         Number(h.total_unrealized_pnl),
        pnl_pct:     Number(h.total_unrealized_pnl_pct),
        live:        false,
      }));

    if (summary) {
      historical.push({
        date:        today,
        marketValue: Number(summary.total_market_value),
        pnl:         Number(summary.total_unrealized_pnl),
        pnl_pct:     Number(summary.total_unrealized_pnl_pct),
        live:        true,
      });
    }

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - range);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    const filtered  = historical.filter((p) => p.date >= cutoffStr);

    filtered.sort((a, b) => a.date.localeCompare(b.date));

    return filtered.map((p) => ({
      ...p,
      value: mode === "value" ? p.marketValue : p.pnl,
    }));
  }, [history, summary, range, mode]);

  const startValue = points[0]?.value ?? 0;
  const endValue   = points[points.length - 1]?.value ?? 0;
  const delta      = endValue - startValue;
  const deltaPct   = startValue !== 0 ? (delta / Math.abs(startValue)) * 100 : 0;

  if (loading) {
    return (
      <div className="w-full">
        <Controls
          mode={mode} setMode={setMode}
          range={range} setRange={setRange}
          delta={null} deltaPct={null}
        />
        <div className="w-full h-[280px] skeleton rounded-lg" />
      </div>
    );
  }

  if (points.length === 0) {
    return (
      <div className="w-full">
        <Controls
          mode={mode} setMode={setMode}
          range={range} setRange={setRange}
          delta={null} deltaPct={null}
        />
        <div className="w-full h-[280px] flex items-center justify-center text-center px-4">
          <div className="font-mono text-sm text-ink-muted max-w-sm">
            No data yet for this range. Add a position to start tracking your P&amp;L.
          </div>
        </div>
      </div>
    );
  }

  const values = points.map((p) => p.value);
  let yMin = Math.min(...values);
  let yMax = Math.max(...values);
  const yPad = Math.max((yMax - yMin) * 0.10, Math.abs(yMax) * 0.05, 1);
  yMin -= yPad;
  yMax += yPad;
  if (yMin === yMax) { yMin -= 1; yMax += 1; }

  const innerW = VIEW_W - PAD.left - PAD.right;
  const innerH = VIEW_H - PAD.top  - PAD.bottom;

  const xScale = (i: number) =>
    PAD.left + (i / Math.max(points.length - 1, 1)) * innerW;
  const yScale = (v: number) =>
    PAD.top + ((yMax - v) / (yMax - yMin)) * innerH;

  const yTicks = Array.from({ length: 5 }, (_, i) => {
    const v = yMin + ((yMax - yMin) * i) / 4;
    return { value: v, y: yScale(v) };
  });

  const tickCount = Math.min(5, points.length);
  const xTicks = Array.from({ length: tickCount }, (_, i) => {
    const idx = Math.floor((i / Math.max(tickCount - 1, 1)) * (points.length - 1));
    return { x: xScale(idx), date: points[idx].date };
  });

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(i)} ${yScale(p.value)}`)
    .join(" ");

  const baselineV = mode === "pnl" && yMin < 0 && yMax > 0 ? 0 : yMin;
  const baselineY = yScale(baselineV);
  const fillPath  =
    linePath +
    ` L ${xScale(points.length - 1)} ${baselineY}` +
    ` L ${xScale(0)} ${baselineY} Z`;

  const isUp = endValue >= startValue;
  const lineColor =
    mode === "pnl"
      ? (endValue >= 0 ? "#00FFAA" : "#FF3366")
      : (isUp        ? "#00FFAA" : "#FF3366");

  const hoverPoint = hoverIdx !== null ? points[hoverIdx] : null;

  return (
    <div className="w-full">
      <Controls
        mode={mode} setMode={setMode}
        range={range} setRange={setRange}
        delta={delta} deltaPct={deltaPct}
      />

      <div className="relative">
        {hoverPoint && (
          <div className="absolute top-0 right-0 bg-bg-deepest border border-line-strong rounded-lg px-3 py-2 z-10 font-mono text-xs pointer-events-none shadow-xl">
            <div className="text-ink-faint mb-1 flex items-center gap-2">
              {fmtLongDate(hoverPoint.date)}
              {hoverPoint.live && (
                <span className="inline-flex items-center gap-1 text-accent">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-glow" />
                  LIVE
                </span>
              )}
            </div>
            <div className="text-ink font-semibold text-sm mb-0.5">
              {fmtCurrency(hoverPoint.marketValue)}
            </div>
            <div className={pnlClass(hoverPoint.pnl)}>
              {fmtCurrency(hoverPoint.pnl, { sign: true })}{" "}
              ({fmtPercent(hoverPoint.pnl_pct, { sign: true })})
            </div>
          </div>
        )}

        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          className="w-full h-[280px]"
          preserveAspectRatio="none"
          onMouseLeave={() => setHoverIdx(null)}
        >
          <defs>
            <linearGradient id="pnlChartFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor={lineColor} stopOpacity="0.25" />
              <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
            </linearGradient>
          </defs>

          {yTicks.map((t, i) => (
            <g key={`y-${i}`}>
              <line
                x1={PAD.left} y1={t.y}
                x2={VIEW_W - PAD.right} y2={t.y}
                stroke="rgba(255,255,255,0.04)"
                strokeWidth="1"
              />
              <text
                x={PAD.left - 8} y={t.y + 4}
                textAnchor="end"
                fontSize="10"
                fontFamily="JetBrains Mono, monospace"
                fill="#5F6A7A"
              >
                {fmtCurrency(t.value, { compact: true })}
              </text>
            </g>
          ))}

          {xTicks.map((t, i) => (
            <text
              key={`x-${i}`}
              x={t.x} y={VIEW_H - PAD.bottom + 18}
              textAnchor="middle"
              fontSize="10"
              fontFamily="JetBrains Mono, monospace"
              fill="#5F6A7A"
            >
              {fmtShortDate(t.date)}
            </text>
          ))}

          <path d={fillPath} fill="url(#pnlChartFill)" />

          {mode === "pnl" && yMin < 0 && yMax > 0 && (
            <line
              x1={PAD.left}            y1={yScale(0)}
              x2={VIEW_W - PAD.right}  y2={yScale(0)}
              stroke="rgba(255,255,255,0.15)"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
          )}

          <path
            d={linePath}
            stroke={lineColor}
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {points.length > 0 && (
            <g>
              <circle
                cx={xScale(points.length - 1)}
                cy={yScale(points[points.length - 1].value)}
                r="10"
                fill={lineColor}
                opacity="0.3"
                className="animate-pulse-glow"
              />
              <circle
                cx={xScale(points.length - 1)}
                cy={yScale(points[points.length - 1].value)}
                r="4"
                fill={lineColor}
              />
            </g>
          )}

          {hoverIdx !== null && hoverIdx !== points.length - 1 && (
            <g>
              <line
                x1={xScale(hoverIdx)} y1={PAD.top}
                x2={xScale(hoverIdx)} y2={VIEW_H - PAD.bottom}
                stroke="rgba(255,255,255,0.15)"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              <circle
                cx={xScale(hoverIdx)}
                cy={yScale(points[hoverIdx].value)}
                r="5"
                fill={lineColor}
                stroke="#0A0E14"
                strokeWidth="2"
              />
            </g>
          )}

          {points.map((_, i) => {
            const left  = i === 0
              ? PAD.left
              : (xScale(i) + xScale(i - 1)) / 2;
            const right = i === points.length - 1
              ? VIEW_W - PAD.right
              : (xScale(i) + xScale(i + 1)) / 2;
            return (
              <rect
                key={`hit-${i}`}
                x={left} y={PAD.top}
                width={right - left} height={innerH}
                fill="transparent"
                onMouseEnter={() => setHoverIdx(i)}
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
}

// ─── Controls ──────────────────────────────────────────────────────

function Controls({
  mode, setMode, range, setRange, delta, deltaPct,
}: {
  mode:  Mode;  setMode:  (m: Mode)  => void;
  range: Range; setRange: (r: Range) => void;
  delta: number | null;
  deltaPct: number | null;
}) {
  return (
    <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="inline-flex items-center gap-0.5 p-0.5 rounded-md bg-bg-card border border-line">
          <ToggleButton active={mode === "value"} onClick={() => setMode("value")}>
            Portfolio value
          </ToggleButton>
          <ToggleButton active={mode === "pnl"} onClick={() => setMode("pnl")}>
            P&amp;L
          </ToggleButton>
        </div>

        {delta !== null && deltaPct !== null && (
          <div className="font-mono text-xs flex items-center gap-2">
            <span className={pnlClass(delta)}>
              {fmtCurrency(delta, { sign: true })} ({fmtPercent(deltaPct, { sign: true })})
            </span>
            <span className="text-ink-faint">over {range}d</span>
          </div>
        )}
      </div>

      <div className="inline-flex items-center gap-0.5 p-0.5 rounded-md bg-bg-card border border-line">
        {([7, 30, 90] as Range[]).map((d) => (
          <ToggleButton key={d} active={range === d} onClick={() => setRange(d)}>
            {d}d
          </ToggleButton>
        ))}
      </div>
    </div>
  );
}

function ToggleButton({
  active, onClick, children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 font-mono text-[11px] rounded transition-colors ${
        active
          ? "bg-accent/15 text-accent"
          : "text-ink-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

// ─── Date formatters ───────────────────────────────────────────────

function fmtShortDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function fmtLongDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}
