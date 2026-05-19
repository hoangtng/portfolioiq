"""
Phase 3 Celery task (fixed).

  take_portfolio_snapshot — runs Mon-Fri at 21:00 UTC (30 min after NYSE close)

Bug fixes vs. original:
  - Distinguishes between "newly created" and "already existed today"
    so the operational log line doesn't lie about what happened.
    `taken` now means freshly captured. `already_existed` is a new key.
"""

import logging
from datetime import date

from celery import shared_task
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User   = get_user_model()


@shared_task(name="analytics.take_portfolio_snapshot")
def take_portfolio_snapshot() -> dict:
    """Daily snapshot for every user with at least one open position."""
    from apps.analytics.services import AnalyticsService
    from apps.portfolio.models import Position
    from apps.portfolio.models_snapshot import PortfolioSnapshot

    user_ids = (
        Position.objects.filter(is_open=True)
        .values_list("user_id", flat=True).distinct()
    )

    today = date.today()
    results = {
        "taken":           0,   # newly created snapshots
        "already_existed": 0,   # idempotent re-runs that found an existing row
        "skipped":         0,   # users with positions but no cached quotes
        "errors":          0,
        "users":           [],
    }

    for user_id in user_ids:
        try:
            # Check existence BEFORE calling so we can distinguish what
            # take_snapshot actually did.
            existed = PortfolioSnapshot.objects.filter(
                user_id=user_id, date=today,
            ).exists()

            user     = User.objects.get(id=user_id)
            snapshot = AnalyticsService(user).take_snapshot()

            if snapshot is None:
                results["skipped"] += 1
            elif existed:
                results["already_existed"] += 1
            else:
                results["taken"] += 1
                results["users"].append({
                    "user":  user.email,
                    "date":  str(snapshot.date),
                    "value": float(snapshot.total_market_value),
                })

        except Exception as exc:
            results["errors"] += 1
            logger.exception("Snapshot failed for user_id=%s: %s", user_id, exc)

    logger.info(
        "take_portfolio_snapshot — taken: %d, already_existed: %d, skipped: %d, errors: %d",
        results["taken"], results["already_existed"], results["skipped"], results["errors"],
    )
    return results
