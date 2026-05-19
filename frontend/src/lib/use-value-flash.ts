"use client";

/**
 * useValueFlash — returns a className that flashes green or red for a
 * brief moment when the watched numeric value changes. Use to make
 * stat-card values visibly "tick" when polling brings new data.
 *
 * Example:
 *   const flash = useValueFlash(totalValue);
 *   <div className={`stat-value ${flash}`}>{fmtCurrency(totalValue)}</div>
 */

import { useEffect, useRef, useState } from "react";

export function useValueFlash(
  value: number | null | undefined,
  durationMs = 800,
): string {
  const previousRef = useRef<number | null | undefined>(value);
  const [flash, setFlash] = useState<"up" | "down" | "">("");

  useEffect(() => {
    const prev = previousRef.current;
    if (
      prev !== undefined && prev !== null &&
      value !== undefined && value !== null &&
      value !== prev
    ) {
      setFlash(value > prev ? "up" : "down");
      const t = setTimeout(() => setFlash(""), durationMs);
      previousRef.current = value;
      return () => clearTimeout(t);
    }
    previousRef.current = value;
  }, [value, durationMs]);

  if (flash === "up")   return "value-flash-up";
  if (flash === "down") return "value-flash-down";
  return "";
}
