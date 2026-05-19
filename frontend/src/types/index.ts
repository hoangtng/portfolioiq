// API response types — keep in sync with backend serializers.
// One interface per backend serializer, named to match.

// ─── Users ────────────────────────────────────────────────────

export interface User {
  id:               number;
  email:            string;
  username:         string;
  first_name:       string;
  last_name:        string;
  display_name:     string;
  avatar_url:       string;
  bio:              string;
  telegram_chat_id: string;
  created_at:       string;
}

export interface TokenPair {
  access:  string;
  refresh: string;
}

export interface GoogleLoginResponse extends TokenPair {
  created: boolean;
}

// ─── Portfolio ────────────────────────────────────────────────

export type AssetType = "stock" | "call" | "put";

export interface Position {
  id:           number;
  ticker:       string;
  asset_type:   AssetType;
  quantity:     string;          // Decimal-as-string from DRF
  avg_cost:     string;
  strike:       string | null;
  expiry:       string | null;   // YYYY-MM-DD
  is_open:      boolean;
  opened_at:    string;
  closed_at:    string | null;
  cost_basis:   string;
  // Enriched from Redis — null on cache miss
  current_price:      string | null;
  unrealized_pnl:     string | null;
  unrealized_pnl_pct: string | null;
  market_value:       string | null;
  trades:             Trade[];
}

export type TradeSide = "buy" | "sell";

export interface Trade {
  id:           number;
  side:         TradeSide;
  quantity:     string;
  price:        string;
  fees:         string;
  executed_at:  string;
  realized_pnl: string | null;
  notes:        string;
  total_value:  string;
  created_at:   string;
}

export interface PortfolioSummary {
  total_cost_basis:          string;
  total_market_value:        string;
  total_unrealized_pnl:      string;
  total_unrealized_pnl_pct:  string;
  positions_count:           number;
  positions:                 Position[];
  prices_cached:             boolean;
}

export type AlertCondition = "above" | "below";

export interface PriceAlert {
  id:              number;
  ticker:          string;
  condition:       AlertCondition;
  target_price:    string;
  is_active:       boolean;
  triggered_at:    string | null;
  triggered_price: string | null;
  created_at:      string;
}

export interface Watchlist {
  id:       number;
  ticker:   string;
  notes:    string;
  added_at: string;
}

export interface Quote {
  ticker:     string;
  price:      number;
  change_pct: number;
  change_abs: number;
  open?:      number | null;
  high?:      number | null;
  low?:       number | null;
  volume?:    number;
  vwap?:      number;
  updated_at?: string;
}

export interface OptionContract {
  ticker:              string;
  strike:              number;
  expiry:              string;
  type:                "call" | "put";
  shares_per_contract: number;
  last_price:          number;
  open:                number;
  high:                number;
  low:                 number;
  volume:              number;
  vwap:                number;
  open_interest:       number;
  iv:                  number;
  break_even:          number;
  delta: number;
  gamma: number;
  theta: number;
  vega:  number;
  underlying_price:  number;
  underlying_ticker: string;
}

export interface OptionsChainResponse {
  ticker:     string;
  contracts:  OptionContract[];
  from_cache: boolean;
  count:      number;
}

// ─── Journal ──────────────────────────────────────────────────

export interface JournalEntry {
  id:           number;
  title:        string;
  body:         string;
  ticker:       string;
  tags:         string[];
  ai_generated: boolean;
  created_at:   string;
  updated_at:   string;
}

export interface JournalSearchResult {
  id:           number;
  title:        string;
  body:         string;
  ticker:       string;
  tags:         string[];
  ai_generated: boolean;
  created_at:   string | null;
  highlight:    { title?: string; body?: string };
  score:        number | null;
}

export interface JournalSearchResponse {
  backend:   "elasticsearch" | "postgres";
  total:     number;
  page:      number;
  page_size: number;
  results:   JournalSearchResult[];
}

// ─── AI ───────────────────────────────────────────────────────

export interface AsyncTaskResponse {
  task_id:          string;
  telegram_notify?: boolean;
  saves_to_journal?: boolean;
}

// Inner result returned by the agent task itself
export type AgentResult =
  | { status: "ok"; response: string; saved_entry_id?: number }
  | { status: "error"; error: string };

// Outer envelope returned by GET /api/ai/result/<task_id>/
export type TaskResult =
  | { status: "pending" }
  | { status: "started" }
  | { status: "success"; data: AgentResult }
  | { status: "failure"; error: string };

export interface ChatResponse {
  answer: string;
}

// ─── Analytics ────────────────────────────────────────────────

export interface PnLHistoryItem {
  date:                     string;
  total_market_value:       number;
  total_unrealized_pnl:     number;
  total_unrealized_pnl_pct: number;
  total_realized_pnl:       number;
}

export interface PnLHistoryResponse {
  days:    number;
  count:   number;
  history: PnLHistoryItem[];
}

export interface PerformanceStats {
  total_trades:         number;
  win_count:            number;
  loss_count:           number;
  win_rate:             number;
  avg_win:              number;
  avg_loss:             number;
  profit_factor:        number | null;
  total_realized_pnl:   number;
  total_unrealized_pnl: number;
  total_pnl:            number;
  best_day:             { date: string | null; value: number | null };
  worst_day:            { date: string | null; value: number | null };
}

export interface Performer {
  id:           number;
  ticker:       string;
  asset_type:   AssetType;
  pnl:          number;
  pnl_pct:      number;
  market_value: number;
  strike:       number | null;
  expiry:       string | null;
}

export interface TopPerformers {
  best:  Performer[];
  worst: Performer[];
}

export interface AllocationItem {
  name:  string;
  value: number;
  pct:   number;
}

export interface AssetAllocation {
  total_value: number;
  by_type:     AllocationItem[];
  by_ticker:   AllocationItem[];
}

export interface RealizedSummary {
  total_realized_pnl: number;
  by_ticker: { ticker: string; pnl: number }[];
  by_month:  { month: string; pnl: number }[];
}

// ─── Paginated list shape ────────────────────────────────────

export interface Paginated<T> {
  count:    number;
  next:     string | null;
  previous: string | null;
  results:  T[];
}