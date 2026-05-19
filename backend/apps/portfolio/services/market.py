"""
yfinance (Yahoo) — market data client.

Drop-in replacement for the Polygon/Massive client. Same public API so
calling code (services, tasks, views) doesn't need to change.

Pros:
  - Free, no API key required
  - Both stock prices AND options chains
  - Bulk price fetches via yf.download

Cons:
  - ~15-minute delayed data (no real-time)
  - Yahoo can rate-limit aggressive polling — keep refreshes to once per minute
  - VWAP not provided — approximated as typical price (H+L+C)/3
  - Greeks not provided by Yahoo — computed locally via Black-Scholes below
  - Commercial use is in a gray area per Yahoo's TOS

For real-time or commercial use, switch back to Polygon.

Docs: https://ranaroussi.github.io/yfinance/
"""

import logging
from datetime import date
from math import erf, exp, log, pi, sqrt
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MassiveError(Exception):
    """Raised on non-recoverable market data errors."""


# Backwards-compatible aliases
PolygonError  = MassiveError
YFinanceError = MassiveError


# ─── Internal helpers ──────────────────────────────────────────

def _safe_float(value) -> Optional[float]:
    """Convert to float, return None on NaN/None/error."""
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int:
    """Convert to int, return 0 on NaN/None/error."""
    try:
        if value is None or pd.isna(value):
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


# ─── Black-Scholes Greeks (Yahoo doesn't provide them) ─────────

_RISK_FREE_RATE = 0.05  # 5% — adjust if rates shift materially

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))

def _norm_pdf(x: float) -> float:
    return exp(-x * x / 2.0) / sqrt(2.0 * pi)


def _bs_greeks(
    spot:        float,
    strike:      float,
    days_to_exp: int,
    iv:          float,
    option_type: str,
    r:           float = _RISK_FREE_RATE,
) -> dict[str, float]:
    """Black-Scholes Greeks. Returns zeros for degenerate inputs."""
    if days_to_exp <= 0 or iv <= 0 or spot <= 0 or strike <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    T  = days_to_exp / 365.0
    d1 = (log(spot / strike) + (r + iv * iv / 2.0) * T) / (iv * sqrt(T))
    d2 = d1 - iv * sqrt(T)

    if option_type.lower() == "call":
        delta = _norm_cdf(d1)
        theta = (
            -spot * _norm_pdf(d1) * iv / (2.0 * sqrt(T))
            - r * strike * exp(-r * T) * _norm_cdf(d2)
        ) / 365.0
    else:  # put
        delta = _norm_cdf(d1) - 1.0
        theta = (
            -spot * _norm_pdf(d1) * iv / (2.0 * sqrt(T))
            + r * strike * exp(-r * T) * _norm_cdf(-d2)
        ) / 365.0

    gamma = _norm_pdf(d1) / (spot * iv * sqrt(T))
    vega  = spot * _norm_pdf(d1) * sqrt(T) / 100.0  # per 1% vol change

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 4),
        "theta": round(theta, 4),
        "vega":  round(vega,  4),
    }


# ─── Client ────────────────────────────────────────────────────

class MassiveClient:
    """
    Market data client backed by yfinance.

    Method signatures match the old Polygon client for drop-in replacement.
    No API key required. The __init__ accepts legacy kwargs and ignores them.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Preserved for back-compat with code that passed these; unused.
        self.api_key  = api_key
        self.base_url = base_url

    # ─── Snapshot (multi-ticker) ───────────────────────────────

    def get_snapshot(self, tickers: list[str]) -> dict[str, dict]:
        """
        Latest daily bar + change for multiple tickers in one batched call.

        Returns: { "PLTR": { "price": 23.45, "change_pct": 2.40, ... } }
        """
        if not tickers:
            return {}

        syms = [t.upper() for t in tickers]

        try:
            data = yf.download(
                tickers=syms,
                period="5d",             # buffer for weekends/holidays
                interval="1d",
                progress=False,
                threads=True,
                auto_adjust=False,
                group_by="ticker",
            )
        except Exception as exc:
            logger.error("yfinance download failed: %s", exc)
            raise MassiveError(f"yfinance download failed: {exc}") from exc

        if data is None or data.empty:
            logger.warning("yfinance returned no data for: %s", syms)
            return {}

        result: dict[str, dict] = {}
        for sym in syms:
            try:
                df = data[sym] if len(syms) > 1 else data
                df = df.dropna(subset=["Close"])
                if df.empty:
                    continue

                latest = df.iloc[-1]
                prev   = df.iloc[-2] if len(df) >= 2 else latest

                last_close = float(latest["Close"])
                prev_close = float(prev["Close"])
                change_abs = last_close - prev_close
                change_pct = (change_abs / prev_close * 100) if prev_close else 0.0

                result[sym] = {
                    "price":      last_close,
                    "change_pct": round(change_pct, 4),
                    "change_abs": round(change_abs, 4),
                    "open":       _safe_float(latest.get("Open")),
                    "high":       _safe_float(latest.get("High")),
                    "low":        _safe_float(latest.get("Low")),
                    "volume":     _safe_int(latest.get("Volume")),
                }
            except (KeyError, IndexError, ValueError) as exc:
                logger.warning("Skipping %s in snapshot: %s", sym, exc)
                continue

        return result

    # ─── Previous close ────────────────────────────────────────

    def get_previous_close(self, ticker: str) -> Optional[dict]:
        """Previous trading day's OHLCV for one ticker."""
        try:
            t    = yf.Ticker(ticker.upper())
            hist = t.history(period="5d", interval="1d", auto_adjust=False)
        except Exception as exc:
            logger.error("yfinance prev close failed for %s: %s", ticker, exc)
            return None

        if hist is None or hist.empty:
            return None

        # The "previous" trading day = second-to-last row (last is today/in-progress)
        row = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]

        close      = float(row["Close"])
        open_p     = _safe_float(row.get("Open")) or close
        high       = _safe_float(row.get("High")) or close
        low        = _safe_float(row.get("Low"))  or close
        change_abs = round(close - open_p, 4)
        change_pct = round((change_abs / open_p) * 100, 4) if open_p else 0.0

        return {
            "price":      close,
            "change_pct": change_pct,
            "change_abs": change_abs,
            "open":       open_p,
            "high":       high,
            "low":        low,
            "volume":     _safe_int(row.get("Volume")),
            "vwap":       round((high + low + close) / 3.0, 4),  # typical-price proxy
        }

    def get_previous_close_many(self, tickers: list[str]) -> dict[str, dict]:
        """Batch previous-close. Uses bulk download — one HTTP call total."""
        if not tickers:
            return {}

        syms = [t.upper() for t in tickers]

        try:
            data = yf.download(
                tickers=syms,
                period="5d",
                interval="1d",
                progress=False,
                threads=True,
                auto_adjust=False,
                group_by="ticker",
            )
        except Exception as exc:
            logger.error("yfinance bulk prev close failed: %s", exc)
            return {}

        if data is None or data.empty:
            return {}

        result: dict[str, dict] = {}
        for sym in syms:
            try:
                df = data[sym] if len(syms) > 1 else data
                df = df.dropna(subset=["Close"])
                if df.empty:
                    continue

                # Use second-to-last row as the "previous" close
                row = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]

                close      = float(row["Close"])
                open_p     = _safe_float(row.get("Open")) or close
                high       = _safe_float(row.get("High")) or close
                low        = _safe_float(row.get("Low"))  or close
                change_abs = round(close - open_p, 4)
                change_pct = round((change_abs / open_p) * 100, 4) if open_p else 0.0

                result[sym] = {
                    "price":      close,
                    "change_pct": change_pct,
                    "change_abs": change_abs,
                    "open":       open_p,
                    "high":       high,
                    "low":        low,
                    "volume":     _safe_int(row.get("Volume")),
                    "vwap":       round((high + low + close) / 3.0, 4),
                }
            except (KeyError, IndexError, ValueError) as exc:
                logger.warning("Skipping %s in prev close batch: %s", sym, exc)
                continue

        return result

    # ─── Options chain ─────────────────────────────────────────

    def get_options_chain(
        self,
        ticker:        str,
        expiry:        Optional[str]   = None,
        contract_type: Optional[str]   = None,
        strike_gte:    Optional[float] = None,
        strike_lte:    Optional[float] = None,
        limit:         int             = 100,
    ) -> list[dict]:
        """
        Fetch options chain via Yahoo Finance.

        If expiry is None, only the NEAREST expiry is fetched (one HTTP call).
        Passing a specific expiry like "2025-07-18" fetches just that chain.

        Greeks (delta/gamma/theta/vega) are computed locally via Black-Scholes
        using the implied volatility Yahoo provides.
        """
        try:
            t           = yf.Ticker(ticker.upper())
            expirations = t.options
        except Exception as exc:
            logger.error("yfinance options init failed for %s: %s", ticker, exc)
            return []

        if not expirations:
            logger.warning("No options available for %s", ticker)
            return []

        # Resolve target expiries
        if expiry:
            if expiry not in expirations:
                logger.warning("Expiry %s not in %s available: %s", expiry, ticker, expirations[:3])
                return []
            target_expiries = [expiry]
        else:
            today_iso       = date.today().isoformat()
            future          = [e for e in expirations if e >= today_iso]
            target_expiries = future[:1] if future else []  # nearest only

        # Underlying spot price — single fetch, reused for all contracts/Greeks
        try:
            underlying_price = float(t.fast_info.get("lastPrice") or 0)
        except Exception:
            underlying_price = 0.0

        contracts: list[dict] = []

        for exp_str in target_expiries:
            try:
                chain = t.option_chain(exp_str)
            except Exception as exc:
                logger.warning("Failed to fetch chain %s @ %s: %s", ticker, exp_str, exc)
                continue

            # Days to expiry — for Black-Scholes T
            try:
                days_to_exp = (date.fromisoformat(exp_str) - date.today()).days
            except ValueError:
                days_to_exp = 0

            # Which side(s) of the chain
            frames: list[tuple[str, pd.DataFrame]] = []
            if contract_type is None or contract_type.lower() == "call":
                frames.append(("call", chain.calls))
            if contract_type is None or contract_type.lower() == "put":
                frames.append(("put", chain.puts))

            for c_type, df in frames:
                if df is None or df.empty:
                    continue

                # Strike filters
                if strike_gte is not None:
                    df = df[df["strike"] >= strike_gte]
                if strike_lte is not None:
                    df = df[df["strike"] <= strike_lte]

                df = df.sort_values("strike")

                for _, row in df.iterrows():
                    strike     = float(row["strike"])
                    last_price = _safe_float(row.get("lastPrice")) or 0.0
                    iv         = float(row.get("impliedVolatility") or 0.0)

                    # Break-even
                    break_even = (
                        strike + last_price if c_type == "call"
                        else strike - last_price
                    )

                    # Compute Greeks from IV via Black-Scholes
                    greeks = _bs_greeks(
                        spot=underlying_price,
                        strike=strike,
                        days_to_exp=days_to_exp,
                        iv=iv,
                        option_type=c_type,
                    )

                    contracts.append({
                        "ticker":              row.get("contractSymbol", ""),
                        "strike":              strike,
                        "expiry":              exp_str,
                        "type":                c_type,
                        "shares_per_contract": 100,

                        # Price data
                        "last_price": last_price,
                        "bid":        _safe_float(row.get("bid")) or 0.0,
                        "ask":        _safe_float(row.get("ask")) or 0.0,
                        "open":       0.0,             # yfinance doesn't provide
                        "high":       0.0,
                        "low":        0.0,
                        "volume":     _safe_int(row.get("volume")),
                        "vwap":       last_price,
                        "open_interest": _safe_int(row.get("openInterest")),

                        # IV from Yahoo
                        "iv":          iv,
                        "break_even":  round(break_even, 4),

                        # Greeks computed locally (above)
                        **greeks,

                        "underlying_price":  underlying_price,
                        "underlying_ticker": ticker.upper(),
                    })

                    if len(contracts) >= limit:
                        return contracts

        return contracts


# Backwards-compatible aliases
PolygonClient  = MassiveClient
YFinanceClient = MassiveClient