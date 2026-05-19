"use client";

/**
 * LiveStatus — the small "● live · 4s ago" widget with a refresh button.
 *
 * Three visual states:
 *   live      green pulse, "Xs ago"      — data fresher than `staleAfter`
 *   stale     amber dot, "Xm ago"        — data older than `staleAfter`
 *   error     red dot, "connection lost" — last refresh failed
 *
 * Self-renders every second so the "Xs ago" label ticks visibly.
 */

import { useEffect, useState } from "react";
import { RefreshCw, AlertCircle } from "lucide-react";

interface LiveStatusProps {
  lastUpdated: Date | null;
  refreshing:  boolean;
  error:       unknown;
  onRefresh:   () => void;
  staleAfter?: number;   // ms after which we go amber; default 120000 (2 min)
}

export function LiveStatus({
  lastUpdated, refreshing, error, onRefresh,
  staleAfter = 120_000,
}: LiveStatusProps) {

  // Force a re-render every second so the "Xs ago" label ticks
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const ageMs    = lastUpdated ? Date.now() - lastUpdated.getTime() : null;
  const isStale  = ageMs !== null && ageMs > staleAfter;
  const hasError = error !== null && error !== undefined;

  const dotClass =
    hasError ? "bg-down"  :
    isStale  ? "bg-warn"  :
                "bg-up animate-pulse-glow";

  const labelClass =
    hasError ? "text-down"        :
    isStale  ? "text-warn"        :
                "text-ink-muted";

  let label: string;
  if (hasError) {
    label = "connection lost";
  } else if (ageMs === null) {
    label = "loading…";
  } else {
    label = formatAge(ageMs);
  }

  return (
    <div className="flex items-center gap-2">
      <span className="inline-flex items-center gap-1.5 text-[11px] font-mono">
        <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
        <span className={labelClass}>{label}</span>
      </span>
      <button
        onClick={onRefresh}
        disabled={refreshing}
        className="btn-icon w-7 h-7"
        aria-label="Refresh"
        title="Refresh now"
      >
        {hasError
          ? <AlertCircle className="w-3.5 h-3.5 text-down" />
          : <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
        }
      </button>
    </div>
  );
}

function formatAge(ms: number): string {
  const sec = Math.round(ms / 1000);
  if (sec < 5)     return "just now";
  if (sec < 60)   return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (min < 60)   return `${min}m ago`;
  return `${Math.round(min / 60)}h ago`;
}
