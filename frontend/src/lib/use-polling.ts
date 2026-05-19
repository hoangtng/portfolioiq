"use client";

/**
 * usePolling — fetch on mount, then re-fetch on an interval.
 *
 * Pauses automatically when the browser tab is hidden (Page Visibility API),
 * so a backgrounded tab doesn't keep hitting the API. Resumes — and
 * immediately re-fetches — when the tab comes back.
 *
 * Returns:
 *   data         — last successful result, or null
 *   loading      — true on the initial load only
 *   refreshing   — true during background refreshes (for spinner UI)
 *   lastUpdated  — Date of the last successful fetch
 *   error        — last fetch error, or null
 *   refresh()    — manually trigger a fetch
 *
 * The fetcher should be stable (wrap in useCallback). The hook
 * captures it via ref so the interval doesn't restart on every render.
 */

import { useCallback, useEffect, useRef, useState } from "react";

interface UsePollingOptions {
  interval?:        number;   // ms between fetches; default 20000
  pauseWhenHidden?: boolean;  // default true
  enabled?:         boolean;  // default true
}

export interface UsePollingResult<T> {
  data:        T | null;
  loading:     boolean;
  refreshing:  boolean;
  lastUpdated: Date | null;
  error:       unknown;
  refresh:     () => Promise<void>;
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  options: UsePollingOptions = {},
): UsePollingResult<T> {
  const {
    interval        = 20_000,
    pauseWhenHidden = true,
    enabled         = true,
  } = options;

  const [data,        setData]        = useState<T | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [refreshing,  setRefreshing]  = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error,       setError]       = useState<unknown>(null);

  // Capture the fetcher in a ref so the polling effect can call the
  // latest version without restarting the interval on every render.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  // Track mount state so a slow request that resolves after unmount
  // doesn't try to setState on a dead component.
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const result = await fetcherRef.current();
      if (!mountedRef.current) return;
      setData(result);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      if (!mountedRef.current) return;
      setError(e);
    } finally {
      if (mountedRef.current) {
        setRefreshing(false);
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    refresh();   // initial fetch

    let timerId: ReturnType<typeof setInterval> | null = null;

    const start = () => {
      if (timerId !== null) return;
      timerId = setInterval(refresh, interval);
    };
    const stop = () => {
      if (timerId !== null) {
        clearInterval(timerId);
        timerId = null;
      }
    };

    start();

    if (!pauseWhenHidden) {
      return stop;
    }

    const onVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        // Tab came back — refetch immediately to catch up, then resume polling
        refresh();
        start();
      }
    };

    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refresh, interval, pauseWhenHidden, enabled]);

  return { data, loading, refreshing, lastUpdated, error, refresh };
}
