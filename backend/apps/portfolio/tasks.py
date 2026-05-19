"""
Portfolio Celery tasks. Scheduled every 60s by Celery Beat.

fetch_quotes:
  1. Collect unique tickers from positions + watchlists
  2. Try snapshot (paid plans) — single API call
  3. On 403, fall back to previous-close (free tier)
  4. Write all quotes to Redis

check_price_alerts:
  1. Read active alerts from Postgres
  2. Compare each against cached Redis prices
  3. Fire Telegram notification, mark alert as triggered
"""

import logging
from datetime import datetime, timezone

from celery import shared_task

from .models import PriceAlert, Position, Watchlist
from .services.cache import QuoteCache
from .services.market import MassiveClient, MassiveError

logger = logging.getLogger(__name__)


@shared_task(name="portfolio.fetch_quotes")
def fetch_quotes() -> dict:
    """Fetch latest prices for all tracked tickers, write to Redis."""

    position_tickers  = set(
        Position.objects.filter(is_open=True)
        .values_list("ticker", flat=True).distinct()
    )
    watchlist_tickers = set(
        Watchlist.objects.values_list("ticker", flat=True).distinct()
    )
    all_tickers = position_tickers | watchlist_tickers

    if not all_tickers:
        logger.info("fetch_quotes: no tickers to fetch")
        return {"fetched": 0, "tickers": []}

    # Position tickers first — they power the dashboard.
    # Within each group, alphabetical for determinism.
    ordered = (
        sorted(position_tickers)
        + sorted(watchlist_tickers - position_tickers)
    )

    logger.info("fetch_quotes: fetching %d tickers — %s", len(ordered), ordered)

    client = MassiveClient()
    cache  = QuoteCache()
    quotes: dict = {}

    try:
        # Single API call for all tickers on paid plans
        quotes = client.get_snapshot(ordered)
        logger.info("fetch_quotes: snapshot returned %d/%d", len(quotes), len(ordered))
    except MassiveError as exc:
        if "403" in str(exc):
            logger.warning("fetch_quotes: snapshot not on plan — using prev-close fallback")
        else:
            logger.error("fetch_quotes: snapshot failed — %s", exc)

        # Only fetch tickers not already in cache; order preserved = position tickers first.
        # This avoids burning the free-tier 5 req/min budget on already-valid entries.
        uncached = cache.warm(ordered)
        if uncached:
            logger.info(
                "fetch_quotes: %d/%d tickers need refresh via prev-close",
                len(uncached), len(ordered),
            )
            quotes = client.get_previous_close_many(uncached)
        else:
            logger.info("fetch_quotes: all tickers already cached, skipping prev-close")

    for ticker, quote in quotes.items():
        cache.set(ticker, quote)

    still_missing = [t for t in ordered if t.upper() not in {q.upper() for q in quotes}]
    logger.info(
        "fetch_quotes: cached %d/%d — missing: %s",
        len(quotes), len(ordered), still_missing,
    )
    return {"fetched": len(quotes), "tickers": list(quotes.keys())}


@shared_task(name="portfolio.check_price_alerts")
def check_price_alerts() -> dict:
    """Check active alerts against cached prices. Fire Telegram on trigger."""

    active = PriceAlert.objects.filter(is_active=True).select_related("user")
    if not active.exists():
        return {"checked": 0, "triggered": 0}

    cache    = QuoteCache()
    tickers  = list(active.values_list("ticker", flat=True).distinct())
    quotes   = cache.get_many(tickers)

    triggered = 0
    for alert in active:
        quote = quotes.get(alert.ticker)
        if not quote:
            continue

        current = float(quote["price"])
        target  = float(alert.target_price)

        fired     = False
        direction = ""
        if alert.condition == PriceAlert.COND_ABOVE and current >= target:
            fired, direction = True, "📈 above"
        elif alert.condition == PriceAlert.COND_BELOW and current <= target:
            fired, direction = True, "📉 below"

        if not fired:
            continue

        alert.is_active       = False
        alert.triggered_at    = datetime.now(timezone.utc)
        alert.triggered_price = current
        alert.save(update_fields=["is_active", "triggered_at", "triggered_price"])
        triggered += 1

        # Telegram is added in Phase 2 — gracefully skip if not installed
        if alert.user.telegram_chat_id:
            try:
                from apps.ai.telegram import TelegramService
                TelegramService().send_message(
                    chat_id=alert.user.telegram_chat_id,
                    text=(
                        f"🔔 *Price Alert Triggered*\n\n"
                        f"*{alert.ticker}* is {direction} your target\n"
                        f"Target:  ${target:,.2f}\n"
                        f"Current: ${current:,.2f}"
                    ),
                )
            except ImportError:
                logger.info(
                    "Alert triggered for %s but Telegram not available (Phase 2 not installed)",
                    alert.ticker,
                )

        logger.info(
            "Alert triggered: %s %s $%.2f (current $%.2f) user=%s",
            alert.ticker, alert.condition, target, current, alert.user.email,
        )

    logger.info(
        "check_price_alerts: checked %d, triggered %d",
        active.count(), triggered,
    )
    return {"checked": active.count(), "triggered": triggered}
