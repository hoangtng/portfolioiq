// PortfolioIQ API client.
// One method per backend endpoint, typed to the response shape.
// Auto-refreshes JWT on 401 then retries the original request once.

import type {
  AssetAllocation,
  AsyncTaskResponse,
  ChatResponse,
  GoogleLoginResponse,
  JournalEntry,
  JournalSearchResponse,
  Paginated,
  PerformanceStats,
  PnLHistoryResponse,
  PortfolioSummary,
  Position,
  PriceAlert,
  Quote,
  RealizedSummary,
  TaskResult,
  TokenPair,
  TopPerformers,
  Trade,
  User,
  Watchlist,
  OptionsChainResponse,
} from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Token storage ───────────────────────────────────────────

const ACCESS_KEY  = "piq_access";
const REFRESH_KEY = "piq_refresh";

export const tokens = {
  get access()  { return typeof window !== "undefined" ? localStorage.getItem(ACCESS_KEY)  : null; },
  get refresh() { return typeof window !== "undefined" ? localStorage.getItem(REFRESH_KEY) : null; },
  set(pair: TokenPair) {
    localStorage.setItem(ACCESS_KEY,  pair.access);
    localStorage.setItem(REFRESH_KEY, pair.refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// ─── Core request ────────────────────────────────────────────
// Turn on status if would like to debug status
// status: number;
export class ApiError extends Error {
  data:   unknown;
  constructor(message: string, data?: unknown) {
    super(message);
    // this.status = status;
    this.data   = data;
  }
}

// ─── Error message helpers ───────────────────────────────────

function prettifyNumbers(text: string): string {
  return text.replace(/\b(\d+)\.(\d+)\b/g, (_match, intPart: string, decPart: string) => {
    const trimmed = decPart.replace(/0+$/, "");
    return trimmed ? `${intPart}.${trimmed}` : intPart;
  });
}

function extractMessage(data: unknown, rawText: string): string {
  const wrap = (s: string) => prettifyNumbers(s);

  if (typeof data === "object" && data !== null && !Array.isArray(data)) {
    const d = data as Record<string, unknown>;
    if (typeof d.detail  === "string") return wrap(d.detail);
    if (typeof d.error   === "string") return wrap(d.error);
    if (typeof d.message === "string") return wrap(d.message);
    if (Array.isArray(d.non_field_errors) && typeof d.non_field_errors[0] === "string")
      return wrap(d.non_field_errors[0]);
    for (const [field, value] of Object.entries(d)) {
      if (Array.isArray(value) && typeof value[0] === "string") return wrap(`${field}: ${value[0]}`);
      if (typeof value === "string") return wrap(`${field}: ${value}`);
    }
  }
  if (Array.isArray(data) && typeof data[0] === "string") return wrap(data[0]);
  if (typeof data === "string" && data.trim())            return wrap(data);
  const trimmed = rawText?.trim();
  if (trimmed && !trimmed.startsWith("<") && trimmed.length < 500) return wrap(trimmed);
  return "Request failed. Please try again.";
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  skipAuth?: boolean;
  skipRefresh?: boolean;
}

async function request<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, skipAuth, skipRefresh, headers, ...rest } = options;

  const reqHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string> || {}),
  };

  if (!skipAuth && tokens.access) {
    reqHeaders.Authorization = `Bearer ${tokens.access}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: reqHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // 401 with refresh token available — try refreshing and retry once
  if (resp.status === 401 && !skipAuth && !skipRefresh && tokens.refresh) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request<T>(path, { ...options, skipRefresh: true });
    }
    // Refresh failed — clear tokens and bubble up
    tokens.clear();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  if (!resp.ok) {
    const rawText = await resp.text();
    let data: unknown = null;
    try { data = JSON.parse(rawText); } catch { /* not JSON — keep rawText */ }

    throw new ApiError(extractMessage(data, rawText), data ?? rawText);
  
  }

  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

async function tryRefresh(): Promise<boolean> {
  if (!tokens.refresh) return false;
  try {
    const resp = await fetch(`${API_BASE}/api/auth/token/refresh/`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ refresh: tokens.refresh }),
    });
    if (!resp.ok) return false;
    const data = await resp.json() as TokenPair;
    tokens.set(data);
    return true;
  } catch {
    return false;
  }
}

// ─── Auth ────────────────────────────────────────────────────

export const auth = {
  register: (data: { email: string; password: string; first_name?: string; last_name?: string }) =>
    request<User>("/api/auth/register/", { method: "POST", body: data, skipAuth: true }),

  login: (email: string, password: string) =>
    request<TokenPair>("/api/auth/token/", {
      method: "POST", body: { email, password }, skipAuth: true,
    }),

  google: (id_token: string) =>
    request<GoogleLoginResponse>("/api/auth/google/", {
      method: "POST", body: { id_token }, skipAuth: true,
    }),

  logout: async () => {
    if (tokens.refresh) {
      try {
        await request("/api/auth/logout/", {
          method: "POST", body: { refresh: tokens.refresh },
        });
      } catch { /* ignore — clear anyway */ }
    }
    tokens.clear();
  },

  me:           () => request<User>("/api/auth/me/"),
  updateMe:     (data: Partial<User>) =>
                  request<User>("/api/auth/me/", { method: "PATCH", body: data }),

  changePassword: (data: { current_password: string; new_password: string; confirm_password: string }) =>
    request<{ detail: string }>("/api/auth/change-password/", { method: "POST", body: data }),
};

// ─── Portfolio ───────────────────────────────────────────────

export const portfolio = {
  summary: () => request<PortfolioSummary>("/api/portfolio/summary/"),

  positions: (params?: { is_open?: boolean; ticker?: string }) => {
    const q = new URLSearchParams();
    if (params?.is_open !== undefined) q.set("is_open", String(params.is_open));
    if (params?.ticker)                q.set("ticker", params.ticker);
    return request<Paginated<Position>>(`/api/portfolio/positions/?${q}`);
  },

  position: (id: number) => request<Position>(`/api/portfolio/positions/${id}/`),

  createPosition: (data: {
    ticker: string; asset_type: string; quantity: string; avg_cost: string;
    strike?: string; expiry?: string;
  }) => request<Position>("/api/portfolio/positions/", { method: "POST", body: data }),

  deletePosition: (id: number) =>
    request<void>(`/api/portfolio/positions/${id}/`, { method: "DELETE" }),

  trades: (positionId: number) =>
    request<Paginated<Trade>>(`/api/portfolio/positions/${positionId}/trades/`),

  recordTrade: (positionId: number, data: {
    side: "buy" | "sell"; quantity: string; price: string;
    fees?: string; executed_at?: string; notes?: string;
  }) => request<Trade>(`/api/portfolio/positions/${positionId}/trades/`, {
    method: "POST", body: data,
  }),

  alerts: (activeOnly = false) =>
    request<Paginated<PriceAlert>>(`/api/portfolio/alerts/${activeOnly ? "?active=true" : ""}`),

  createAlert: (data: { ticker: string; condition: "above" | "below"; target_price: string }) =>
    request<PriceAlert>("/api/portfolio/alerts/", { method: "POST", body: data }),

  deleteAlert: (id: number) =>
    request<void>(`/api/portfolio/alerts/${id}/`, { method: "DELETE" }),

  quote: (ticker: string) => request<Quote>(`/api/portfolio/quote/${ticker}/`),

  optionsChain: (
    ticker: string,
    params?: { expiry?: string; type?: "call" | "put"; strike_gte?: number; strike_lte?: number; limit?: number },
  ) => {
    const q = new URLSearchParams();
    if (params?.expiry)      q.set("expiry", params.expiry);
    if (params?.type)        q.set("type", params.type);
    if (params?.strike_gte !== undefined) q.set("strike_gte", String(params.strike_gte));
    if (params?.strike_lte !== undefined) q.set("strike_lte", String(params.strike_lte));
    if (params?.limit)       q.set("limit", String(params.limit));
    return request<OptionsChainResponse>(`/api/portfolio/options/${ticker}/?${q}`);
  },

  watchlist: () => request<Paginated<Watchlist>>("/api/portfolio/watchlist/"),

  addWatchlist: (data: { ticker: string; notes?: string }) =>
    request<Watchlist>("/api/portfolio/watchlist/", { method: "POST", body: data }),

  removeWatchlist: (id: number) =>
    request<void>(`/api/portfolio/watchlist/${id}/`, { method: "DELETE" }),
};

// ─── Journal ─────────────────────────────────────────────────

export const journal = {
  list: (params?: { ticker?: string; tag?: string }) => {
    const q = new URLSearchParams();
    if (params?.ticker) q.set("ticker", params.ticker);
    if (params?.tag)    q.set("tag", params.tag);
    return request<Paginated<JournalEntry>>(`/api/journal/?${q}`);
  },

  get:    (id: number) => request<JournalEntry>(`/api/journal/${id}/`),
  create: (data: { title: string; body: string; ticker?: string; tags?: string[] }) =>
            request<JournalEntry>("/api/journal/", { method: "POST", body: data }),
  update: (id: number, data: Partial<JournalEntry>) =>
            request<JournalEntry>(`/api/journal/${id}/`, { method: "PATCH", body: data }),
  delete: (id: number) =>
            request<void>(`/api/journal/${id}/`, { method: "DELETE" }),

  search: (params: { q: string; ticker?: string; tag?: string; page_size?: number }) => {
    const qs = new URLSearchParams();
    qs.set("q", params.q);
    if (params.ticker)     qs.set("ticker", params.ticker);
    if (params.tag)        qs.set("tag", params.tag);
    if (params.page_size)  qs.set("page_size", String(params.page_size));
    return request<JournalSearchResponse>(`/api/journal/search/?${qs}`);
  },
};

// ─── AI ──────────────────────────────────────────────────────

export const ai = {
  analyze: () => request<AsyncTaskResponse>("/api/ai/analyze/", { method: "POST", body: {} }),

  generateJournal: (data: { ticker: string; thesis: string; strategy?: string }) =>
    request<AsyncTaskResponse>("/api/ai/journal/", { method: "POST",
      body: {
        trade_data: {
          ticker:   data.ticker,
          raw_note: data.strategy
            ? `${data.thesis}\nStrategy: ${data.strategy}`
            : data.thesis,
        },
      },
    }),

  chat: (message: string, history?: { role: "user" | "assistant"; content: string }[]) =>
    request<ChatResponse>("/api/ai/chat/", { method: "POST", body: { question: message, history } }),

  result: (taskId: string) =>
    request<TaskResult>(`/api/ai/result/${taskId}/`),

  // Poll a task until it finishes or we hit max attempts.
  pollTask: async (taskId: string, opts?: { interval?: number; maxAttempts?: number }) => {
    const interval    = opts?.interval    ?? 2000;
    const maxAttempts = opts?.maxAttempts ?? 60;   // 60 × 2s = 2 minutes
    for (let i = 0; i < maxAttempts; i++) {
      const result = await ai.result(taskId);
      if (result.status !== "pending" && result.status !== "started") return result;
      await new Promise(r => setTimeout(r, interval));
    }
    return { status: "failure" as const, error: "Task timed out" };
  },
};

// ─── Analytics ───────────────────────────────────────────────

export const analytics = {
  history:    (days = 90) => request<PnLHistoryResponse>(`/api/analytics/history/?days=${days}`),
  stats:      () => request<PerformanceStats>("/api/analytics/stats/"),
  performers: (limit = 5) => request<TopPerformers>(`/api/analytics/performers/?limit=${limit}`),
  allocation: () => request<AssetAllocation>("/api/analytics/allocation/"),
  realized:   () => request<RealizedSummary>("/api/analytics/realized/"),
  snapshot:   () => request<unknown>("/api/analytics/snapshot/", { method: "POST", body: {} }),
};

// ─── Health ──────────────────────────────────────────────────

export const health = {
  check: () => request<{ status: string; services: Record<string, string> }>(
    "/health/", { skipAuth: true },
  ),
};




