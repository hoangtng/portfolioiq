"""
Phase 3 — snapshot models.

These live in the portfolio app so they share the same app_label as
Position and Trade (cleaner FK relationships, cleaner migrations).

The analytics app re-exports them from apps.analytics.models so callers
can use either path.

  PortfolioSnapshot  — one row per (user, date)
                       captured at market close by a Celery task
                       powers the historical P&L curve

  PositionSnapshot   — one row per (user, ticker, asset_type, date)
                       powers per-ticker performance breakdown

Both are append-only — never updated, only inserted.

NOTE on `total_realized_pnl`:
  This field stores LIFETIME cumulative realized P&L through that date,
  NOT the realized P&L generated on that date. So snapshot rows for
  consecutive dates will show the same value if no closing trades
  happened between them. Compute day-over-day deltas in the consumer
  if you need per-day realized P&L.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models


class PortfolioSnapshot(models.Model):
    """End-of-day snapshot of total portfolio value."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_snapshots",
    )
    date = models.DateField(db_index=True)

    total_cost_basis         = models.DecimalField(max_digits=18, decimal_places=4)
    total_market_value       = models.DecimalField(max_digits=18, decimal_places=4)
    total_unrealized_pnl     = models.DecimalField(max_digits=18, decimal_places=4)
    total_unrealized_pnl_pct = models.DecimalField(max_digits=10, decimal_places=4)
    total_realized_pnl       = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0"),
        help_text="Lifetime cumulative realized P&L through this date.",
    )
    positions_count = models.IntegerField(default=0)
    prices_captured = models.BooleanField(
        default=True,
        help_text="False if at least one position had no cached price.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "portfolio"
        unique_together = ("user", "date")
        ordering = ["date"]
        indexes = [models.Index(fields=["user", "-date"])]

    def __str__(self):
        return f"{self.user.email} — {self.date} — ${self.total_market_value}"


class PositionSnapshot(models.Model):
    """End-of-day snapshot of a single position."""

    portfolio_snapshot = models.ForeignKey(
        PortfolioSnapshot,
        on_delete=models.CASCADE,
        related_name="position_snapshots",
        null=True, blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="position_snapshots",
    )
    date       = models.DateField(db_index=True)
    ticker     = models.CharField(max_length=16, db_index=True)
    asset_type = models.CharField(max_length=8)

    quantity         = models.DecimalField(max_digits=14, decimal_places=4)
    avg_cost         = models.DecimalField(max_digits=14, decimal_places=4)
    price            = models.DecimalField(max_digits=14, decimal_places=4)
    market_value     = models.DecimalField(max_digits=18, decimal_places=4)
    cost_basis       = models.DecimalField(max_digits=18, decimal_places=4)
    unrealized_pnl   = models.DecimalField(max_digits=18, decimal_places=4)
    unrealized_pnl_pct = models.DecimalField(max_digits=10, decimal_places=4)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "portfolio"
        unique_together = ("user", "date", "ticker", "asset_type")
        ordering = ["date"]
        indexes = [models.Index(fields=["user", "ticker", "-date"])]

    def __str__(self):
        return f"{self.ticker} — {self.date} — ${self.market_value}"
