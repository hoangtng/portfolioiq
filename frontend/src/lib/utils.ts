// Formatters — single source for currency/percent/date/className helpers.

import clsx, { type ClassValue } from "clsx";

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

// ─── Currency ───────────────────────────────────────────────

export function fmtCurrency(
  value: number | string | null | undefined,
  opts: { compact?: boolean; sign?: boolean; decimals?: number } = {},
): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(num)) return "—";

  const { compact = false, sign = false, decimals = 2 } = opts;
  const abs = Math.abs(num);

  // Compact for >= 10k
  if (compact && abs >= 10_000) {
    const formatted = new Intl.NumberFormat("en-US", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(abs);
    return `${num < 0 ? "-" : sign ? "+" : ""}$${formatted}`;
  }

  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(abs);

  return `${num < 0 ? "-" : sign ? "+" : ""}$${formatted}`;
}

// ─── Percent ────────────────────────────────────────────────

export function fmtPercent(
  value: number | string | null | undefined,
  opts: { sign?: boolean; decimals?: number } = {},
): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(num)) return "—";

  const { sign = false, decimals = 2 } = opts;
  const formatted = Math.abs(num).toFixed(decimals);
  return `${num < 0 ? "-" : sign ? "+" : ""}${formatted}%`;
}

// ─── Plain number ───────────────────────────────────────────

export function fmtNumber(
  value: number | string | null | undefined,
  decimals = 2,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(num)) return "—";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
}

// ─── P&L color classes ──────────────────────────────────────

export function pnlClass(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "text-ink-dim";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(num) || num === 0) return "text-ink-dim";
  return num > 0 ? "text-up" : "text-down";
}

// ─── Date formatters ────────────────────────────────────────

export function fmtDate(value: string | null | undefined, format: "short" | "long" | "time" | "iso" = "short"): string {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return "—";

  if (format === "iso") return d.toISOString().slice(0, 10);

  if (format === "time") {
    return d.toLocaleString("en-US", {
      month: "short", day: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  if (format === "long") {
    return d.toLocaleDateString("en-US", {
      year: "numeric", month: "long", day: "numeric",
    });
  }

  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ─── Time-ago ───────────────────────────────────────────────

export function timeAgo(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return "—";
  const sec = Math.round((Date.now() - d.getTime()) / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.round(hr / 24);
  if (days < 30) return `${days}d ago`;
  return fmtDate(value);
}

// ─── Ticker initial (for avatar) ────────────────────────────

export function tickerInitial(ticker: string): string {
  return ticker.slice(0, 4).toUpperCase();
}

// ─── Days until expiry ──────────────────────────────────────

export function daysUntil(date: string | null | undefined): number | null {
  if (!date) return null;
  const target = new Date(date);
  const today  = new Date();
  if (isNaN(target.getTime())) return null;
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export type MarketState = "Open" | "Pre Market" | "After Hours" | "Closed";

// NYSE/NASDAQ full-day closures. Update yearly.
const US_MARKET_HOLIDAYS = new Set<string>([
  // 2025
  "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
  "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01",
  "2025-11-27", "2025-12-25",
  // 2026
  "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
  "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
  "2026-11-26", "2026-12-25",
]);

export function getMarketStatus(now: Date = new Date()): {
  state:  MarketState;
  nyTime: string;       // "14:23"
} {
  // Read the current time in New York — Intl handles EST/EDT automatically
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday:  "short",
    year:     "numeric",
    month:    "2-digit",
    day:      "2-digit",
    hour:     "2-digit",
    minute:   "2-digit",
    hour12:   false,
  }).formatToParts(now);

  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";

  const weekday = get("weekday");
  const dateKey = `${get("year")}-${get("month")}-${get("day")}`;
  let   hour    = parseInt(get("hour"),   10);
  const minute  = parseInt(get("minute"), 10);
  if (hour === 24) hour = 0;          // Intl quirk at midnight

  const nyTime = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  const mins   = hour * 60 + minute;

  // Weekend or holiday — closed all day
  if (weekday === "Sat" || weekday === "Sun") return { state: "Closed", nyTime };
  if (US_MARKET_HOLIDAYS.has(dateKey))         return { state: "Closed", nyTime };

  // Trading windows (in NY minutes since midnight)
  if (mins <  4 * 60)        return { state: "Closed",      nyTime };  //  < 04:00
  if (mins <  9 * 60 + 30)   return { state: "Pre Market",  nyTime };  //  04:00 – 09:30
  if (mins < 16 * 60)        return { state: "Open",        nyTime };  //  09:30 – 16:00
  if (mins < 20 * 60)        return { state: "After Hours", nyTime };  //  16:00 – 20:00
  return { state: "Closed", nyTime };                                   //  20:00 – 04:00
}