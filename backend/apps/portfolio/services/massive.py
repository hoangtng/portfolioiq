"""
MassiveClient — market data client for Massive (formerly Polygon.io).

Polygon.io rebranded to massive.com in 2025. Base URL, options chain
response field names, and v3 pagination all changed.

Docs:  https://massive.com/docs/rest/
Keys:  https://massive.com/dashboard/signup  (free tier works for dev)

Plan notes:
  Stocks Basic (free):
    /v2/aggs/ticker/{t}/prev   ← always works
    /v2/snapshot/...           ← 403 (use prev-close fallback)
    5 calls/min

  Stocks Starter ($29/mo):
    /v2/snapshot/...           ← 15-min delayed
    /v3/snapshot               ← unified, 15-min delayed

  Options Starter ($29/mo):
    /v3/snapshot/options/...   ← Greeks + IV, 15-min delayed
"""

import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.massive.com"


class MassiveError(Exception):
    """Raised on non-recoverable Massive API errors."""


# Backwards-compatible alias
PolygonError = MassiveError


class MassiveClient:

    def __init__(self):
        self.api_key  = settings.POLYGON_API_KEY
        self.base_url = BASE_URL

    # ─── Private helpers ──────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict:
        url    = f"{self.base_url}{path}"
        params = {**(params or {}), "apiKey": self.api_key}

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code == 401:
                raise MassiveError("401 — check POLYGON_API_KEY in .env") from exc
            if code == 403:
                raise MassiveError(
                    f"403 — endpoint not on your plan: {path}"
                ) from exc
            if code == 429:
                raise MassiveError(
                    "429 — rate limit hit (free tier: 5 req/min)"
                ) from exc
            raise MassiveError(f"HTTP {code}: {path}") from exc
        except httpx.TimeoutException as exc:
            raise MassiveError(f"timeout: {path}") from exc
        except httpx.RequestError as exc:
            raise MassiveError(f"network error: {exc}") from exc

    def _paginate(self, path: str, params: dict | None = None,
                  max_results: int = 250) -> list:
        """Follow Massive's next_url cursor pagination."""
        results        = []
        current_url    = f"{self.base_url}{path}"
        current_params = {**(params or {}), "apiKey": self.api_key}

        while True:
            try:
                with httpx.Client(timeout=10) as client:
                    resp = client.get(current_url, params=current_params)
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                if code == 403:
                    raise MassiveError(f"403 — endpoint not on your plan: {path}") from exc
                if code == 429:
                    raise MassiveError("429 — rate limit hit") from exc
                raise MassiveError(f"HTTP {code}") from exc
            except httpx.RequestError as exc:
                raise MassiveError(f"network error: {exc}") from exc

            results.extend(data.get("results", []))
            if len(results) >= max_results:
                break

            next_url = data.get("next_url")
            if not next_url:
                break

            current_url    = next_url
            current_params = {"apiKey": self.api_key}

        return results[:max_results]

    # ─── Snapshot (multi-ticker, Starter+) ────────────────────

    def get_snapshot(self, tickers: list[str]) -> dict[str, dict]:
        """
        Fetch latest daily bar + change for multiple tickers in one call.

        Endpoint:  /v2/snapshot/locale/us/markets/stocks/tickers
        Returns:   { "PLTR": { "price": 23.45, "change_pct": 2.40, ... } }
        Free tier returns 403 — caller should fall back.
        """
        if not tickers:
            return {}

        try:
            data = self._get(
                "/v2/snapshot/locale/us/markets/stocks/tickers",
                params={"tickers": ",".join(t.upper() for t in tickers)},
            )
        except MassiveError as exc:
            logger.error("Massive snapshot failed: %s", exc)
            raise

        result: dict[str, dict] = {}
        for item in data.get("tickers", []):
            ticker = item.get("ticker", "")
            if not ticker:
                continue

            day  = item.get("day")     or {}
            prev = item.get("prevDay") or {}
            price = day.get("c") or prev.get("c")
            if not price:
                continue

            result[ticker] = {
                "price":      float(price),
                "change_pct": round(float(item.get("todaysChangePerc") or 0), 4),
                "change_abs": round(float(item.get("todaysChange")     or 0), 4),
                "open":       float(day.get("o") or prev.get("o") or 0) or None,
                "high":       float(day.get("h") or prev.get("h") or 0) or None,
                "low":        float(day.get("l") or prev.get("l") or 0) or None,
                "volume":     int(  day.get("v") or prev.get("v") or 0),
            }
        return result

    # ─── Previous close (free-tier safe) ──────────────────────

    def get_previous_close(self, ticker: str) -> dict | None:
        """
        Previous trading day's OHLCV for one ticker.
        Endpoint: /v2/aggs/ticker/{ticker}/prev — works on all plans.
        """
        try:
            data = self._get(f"/v2/aggs/ticker/{ticker.upper()}/prev")
        except MassiveError as exc:
            logger.error("Massive prev close failed for %s: %s", ticker, exc)
            return None

        results = data.get("results", [])
        if not results:
            return None

        r     = results[0]
        close = r.get("c")
        if not close:
            return None

        open_p     = float(r.get("o") or close)
        change_abs = round(float(close) - open_p, 4)
        change_pct = round((change_abs / open_p) * 100, 4) if open_p else 0.0

        return {
            "price":      float(close),
            "change_pct": change_pct,
            "change_abs": change_abs,
            "open":       open_p,
            "high":       float(r.get("h") or close),
            "low":        float(r.get("l") or close),
            "volume":     int(r.get("v") or 0),
            "vwap":       float(r.get("vw") or close),
        }

    def get_previous_close_many(self, tickers: list[str]) -> dict[str, dict]:
        """Batch prev-close. One API call per ticker. Free-tier fallback."""
        results = {}
        for ticker in tickers:
            quote = self.get_previous_close(ticker)
            if quote:
                results[ticker.upper()] = quote
        return results

    # ─── Options chain ────────────────────────────────────────

    def get_options_chain(
        self,
        ticker:        str,
        expiry:        str   | None = None,
        contract_type: str   | None = None,
        strike_gte:    float | None = None,
        strike_lte:    float | None = None,
        limit:         int          = 100,
    ) -> list[dict]:
        """
        Fetch options contracts. Returns [] on free tier (403).
        Endpoint:  /v3/snapshot/options/{ticker}
        """
        params: dict = {
            "limit": min(limit, 250),
            "sort":  "strike_price",
            "order": "asc",
        }

        if expiry:
            params["expiration_date"] = expiry
        else:
            from datetime import date
            params["expiration_date.gte"] = date.today().isoformat()

        if contract_type:
            params["contract_type"] = contract_type.lower()
        if strike_gte is not None:
            params["strike_price.gte"] = strike_gte
        if strike_lte is not None:
            params["strike_price.lte"] = strike_lte

        try:
            raw = self._paginate(
                f"/v3/snapshot/options/{ticker.upper()}",
                params=params,
                max_results=limit,
            )
        except MassiveError as exc:
            logger.error("Massive options chain failed for %s: %s", ticker, exc)
            return []

        contracts = []
        for item in raw:
            details = item.get("details")          or {}
            greeks  = item.get("greeks")           or {}
            day     = item.get("day")              or {}
            under   = item.get("underlying_asset") or {}

            strike      = details.get("strike_price")
            expiry_date = details.get("expiration_date")
            if not strike or not expiry_date:
                continue

            contracts.append({
                "ticker":              details.get("ticker", ""),
                "strike":              float(strike),
                "expiry":              expiry_date,
                "type":                details.get("contract_type", ""),
                "shares_per_contract": int(details.get("shares_per_contract") or 100),
                "last_price":  float(day.get("close")  or 0),
                "open":        float(day.get("open")   or 0),
                "high":        float(day.get("high")   or 0),
                "low":         float(day.get("low")    or 0),
                "volume":      int(  day.get("volume") or 0),
                "vwap":        float(day.get("vwap")   or 0),
                "open_interest": int(  item.get("open_interest")     or 0),
                "iv":            float(item.get("implied_volatility") or 0),
                "break_even":    float(item.get("break_even_price")   or 0),
                "delta": float(greeks.get("delta") or 0),
                "gamma": float(greeks.get("gamma") or 0),
                "theta": float(greeks.get("theta") or 0),
                "vega":  float(greeks.get("vega")  or 0),
                "underlying_price":  float(under.get("price")  or 0),
                "underlying_ticker": under.get("ticker", ticker.upper()),
            })

        return contracts


# Backwards-compatible alias
PolygonClient = MassiveClient
