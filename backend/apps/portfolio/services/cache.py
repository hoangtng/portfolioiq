"""
QuoteCache — typed Redis wrapper for live price quotes.

Key:     quote:{TICKER}
Value:   JSON {price, change_pct, change_abs, open, high, low, volume, updated_at}
TTL:     120s (Celery refreshes every 60s — 2x safety margin)
"""

import json
import logging
from datetime import datetime, timezone

from django.core.cache import cache

logger = logging.getLogger(__name__)

QUOTE_TTL = 120
QUOTE_KEY = "quote:{}"


class QuoteCache:

    def get(self, ticker: str) -> dict | None:
        try:
            raw = cache.get(QUOTE_KEY.format(ticker.upper()))
            return json.loads(raw) if raw else None
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("QuoteCache.get(%s) failed: %s", ticker, exc)
            return None

    def set(self, ticker: str, quote: dict) -> None:
        try:
            quote = {**quote, "updated_at": datetime.now(timezone.utc).isoformat()}
            cache.set(
                QUOTE_KEY.format(ticker.upper()),
                json.dumps(quote),
                timeout=QUOTE_TTL,
            )
        except Exception as exc:
            logger.warning("QuoteCache.set(%s) failed: %s", ticker, exc)

    def get_many(self, tickers: list[str]) -> dict[str, dict]:
        """Batch fetch. Missing tickers omitted from result."""
        if not tickers:
            return {}

        keys = {QUOTE_KEY.format(t.upper()): t.upper() for t in tickers}
        try:
            raw_map = cache.get_many(list(keys.keys()))
        except Exception as exc:
            logger.warning("QuoteCache.get_many failed: %s", exc)
            return {}

        result = {}
        for key, raw in raw_map.items():
            try:
                result[keys[key]] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
        return result

    def delete(self, ticker: str) -> None:
        cache.delete(QUOTE_KEY.format(ticker.upper()))

    def warm(self, tickers: list[str]) -> list[str]:
        """Return tickers NOT currently in the cache."""
        cached = set(self.get_many(tickers).keys())
        return [t for t in tickers if t.upper() not in cached]
