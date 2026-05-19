"""
Phase 1 — portfolio models.

Four models:
  Watchlist   — user follows a ticker (no position required)
  Position    — open or closed holding (stock, call, or put)
  Trade       — every buy/sell against a position with realized P&L
  PriceAlert  — above/below price target with Telegram delivery
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


# ─── Watchlist ────────────────────────────────────────────────

class Watchlist(models.Model):
    """A ticker the user follows. Gets price-fetched by Celery."""

    user      = models.ForeignKey(User, on_delete=models.CASCADE,
                                  related_name="watchlists")
    ticker    = models.CharField(max_length=16)
    notes     = models.TextField(blank=True)
    added_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "ticker")
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.user.email} — {self.ticker}"


# ─── Position ─────────────────────────────────────────────────

class Position(models.Model):
    """An open or closed holding."""

    ASSET_STOCK = "stock"
    ASSET_CALL  = "call"
    ASSET_PUT   = "put"
    ASSET_TYPES = [
        (ASSET_STOCK, "Stock"),
        (ASSET_CALL,  "Call Option"),
        (ASSET_PUT,   "Put Option"),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name="positions")
    ticker     = models.CharField(max_length=16, db_index=True)
    asset_type = models.CharField(max_length=8, choices=ASSET_TYPES,
                                   default=ASSET_STOCK)
    quantity   = models.DecimalField(max_digits=14, decimal_places=4)
    avg_cost   = models.DecimalField(max_digits=14, decimal_places=4)

    # Options-only fields
    strike     = models.DecimalField(max_digits=12, decimal_places=2,
                                      null=True, blank=True)
    expiry     = models.DateField(null=True, blank=True)

    is_open    = models.BooleanField(default=True, db_index=True)
    opened_at  = models.DateTimeField(auto_now_add=True)
    closed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["user", "is_open"]),
            models.Index(fields=["user", "ticker"]),
        ]

    def __str__(self):
        label = f"{self.ticker} {self.asset_type}"
        if self.strike:
            label += f" ${self.strike} {self.expiry}"
        return label

    @property
    def is_option(self) -> bool:
        return self.asset_type in (self.ASSET_CALL, self.ASSET_PUT)

    @property
    def contract_multiplier(self) -> Decimal:
        """Options control 100 shares each. Stocks are 1:1."""
        return Decimal("100") if self.is_option else Decimal("1")

    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.avg_cost * self.contract_multiplier

    def market_value(self, current_price: Decimal) -> Decimal:
        return self.quantity * Decimal(str(current_price)) * self.contract_multiplier

    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        return self.market_value(current_price) - self.cost_basis

    def unrealized_pnl_pct(self, current_price: Decimal) -> Decimal:
        if self.cost_basis == 0:
            return Decimal("0")
        return self.unrealized_pnl(current_price) / self.cost_basis * Decimal("100")


# ─── Trade ────────────────────────────────────────────────────

class Trade(models.Model):
    """A single buy or sell execution against a Position."""

    SIDE_BUY  = "buy"
    SIDE_SELL = "sell"
    SIDES = [(SIDE_BUY, "Buy"), (SIDE_SELL, "Sell")]

    position    = models.ForeignKey(Position, on_delete=models.CASCADE,
                                     related_name="trades")
    side        = models.CharField(max_length=4, choices=SIDES)
    quantity    = models.DecimalField(max_digits=14, decimal_places=4)
    price       = models.DecimalField(max_digits=14, decimal_places=4)
    fees        = models.DecimalField(max_digits=10, decimal_places=2,
                                       default=Decimal("0"))
    executed_at = models.DateTimeField()

    # Set on sells only
    realized_pnl = models.DecimalField(max_digits=14, decimal_places=4,
                                        null=True, blank=True)
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-executed_at"]
        indexes  = [models.Index(fields=["position", "executed_at"])]

    def __str__(self):
        return f"{self.side.upper()} {self.quantity} {self.position.ticker} @ ${self.price}"

    @property
    def total_value(self) -> Decimal:
        return self.quantity * self.price * self.position.contract_multiplier


# ─── Price Alert ──────────────────────────────────────────────

class PriceAlert(models.Model):
    """A price target. Checked every 60s, fires Telegram on trigger."""

    COND_ABOVE = "above"
    COND_BELOW = "below"
    CONDITIONS = [(COND_ABOVE, "Above"), (COND_BELOW, "Below")]

    user         = models.ForeignKey(User, on_delete=models.CASCADE,
                                      related_name="alerts")
    ticker       = models.CharField(max_length=16, db_index=True)
    condition    = models.CharField(max_length=8, choices=CONDITIONS)
    target_price = models.DecimalField(max_digits=14, decimal_places=4)

    is_active    = models.BooleanField(default=True, db_index=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    triggered_price = models.DecimalField(max_digits=14, decimal_places=4,
                                           null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes  = [models.Index(fields=["user", "is_active"])]

    def __str__(self):
        return f"{self.ticker} {self.condition} ${self.target_price}"
