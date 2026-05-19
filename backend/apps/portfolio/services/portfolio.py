"""
PortfolioService — core business logic for the portfolio app.

All operations that span multiple models live here:
  - get_summary()      build the dashboard from positions + Redis prices
  - record_trade()     weighted avg cost on buys, realized P&L on sells
  - get_realized_pnl() total realized across all sell trades
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from ..models import Position, Trade
from .cache import QuoteCache

logger = logging.getLogger(__name__)


class PortfolioService:

    def __init__(self, user):
        self.user  = user
        self.cache = QuoteCache()

    # ─── Summary ──────────────────────────────────────────────

    def get_summary(self) -> dict:
        """
        Build full portfolio summary.

        prices_cached is False when at least one ticker has no Redis entry
        (a fresh portfolio or Celery hasn't run yet).
        """
        positions = list(
            Position.objects.filter(user=self.user, is_open=True)
            .prefetch_related("trades")
        )

        if not positions:
            return {
                "total_cost_basis":          Decimal("0"),
                "total_market_value":        Decimal("0"),
                "total_unrealized_pnl":      Decimal("0"),
                "total_unrealized_pnl_pct":  Decimal("0"),
                "positions_count":           0,
                "positions":                 [],
                "prices_cached":             True,
            }

        tickers = list({p.ticker for p in positions})
        quotes  = self.cache.get_many(tickers)

        total_cost   = Decimal("0")
        total_market = Decimal("0")
        all_priced   = True

        for position in positions:
            total_cost += position.cost_basis
            quote = quotes.get(position.ticker)
            if quote:
                price = Decimal(str(quote["price"]))
                total_market += position.market_value(price)
            else:
                # No cached price — fall back to cost basis for totals
                total_market += position.cost_basis
                all_priced = False

        total_pnl     = total_market - total_cost
        total_pnl_pct = (total_pnl / total_cost * Decimal("100")) if total_cost else Decimal("0")

        return {
            "total_cost_basis":          total_cost.quantize(Decimal("0.01")),
            "total_market_value":        total_market.quantize(Decimal("0.01")),
            "total_unrealized_pnl":      total_pnl.quantize(Decimal("0.01")),
            "total_unrealized_pnl_pct":  total_pnl_pct.quantize(Decimal("0.01")),
            "positions_count":           len(positions),
            "positions":                 positions,
            "prices_cached":             all_priced,
        }

    # ─── Record trade ─────────────────────────────────────────

    @transaction.atomic
    def record_trade(
        self,
        position:    Position,
        side:        str,
        quantity:    Decimal,
        price:       Decimal,
        fees:        Decimal       = Decimal("0"),
        executed_at: datetime|None = None,
        notes:       str           = "",
    ) -> Trade:
        """
        Record a buy or sell against a position.

        Buy:  weighted avg cost recalc, quantity increases.
        Sell: realized P&L calculated, quantity decreases, position closes at 0.
        """
        if executed_at is None:
            executed_at = datetime.now(timezone.utc)

        realized_pnl: Decimal | None = None

        if side == Trade.SIDE_BUY:
            old_cost      = position.quantity * position.avg_cost
            new_cost      = quantity * price + fees   # fees increase cost basis
            new_quantity  = position.quantity + quantity
            position.avg_cost = (old_cost + new_cost) / new_quantity
            position.quantity = new_quantity
            position.save(update_fields=["quantity", "avg_cost"])

        elif side == Trade.SIDE_SELL:
            if quantity > position.quantity:
                raise ValueError(
                    f"Cannot sell {quantity} — position only has {position.quantity}"
                )

            realized_pnl = (
                (price - position.avg_cost) * quantity * position.contract_multiplier
                - fees
            )

            position.quantity -= quantity
            if position.quantity == 0:
                position.is_open   = False
                position.closed_at = executed_at
                position.save(update_fields=["quantity", "is_open", "closed_at"])
            else:
                position.save(update_fields=["quantity"])

        else:
            raise ValueError(f"Unknown side: {side!r}")

        return Trade.objects.create(
            position     = position,
            side         = side,
            quantity     = quantity,
            price        = price,
            fees         = fees,
            executed_at  = executed_at,
            realized_pnl = realized_pnl,
            notes        = notes,
        )

    # ─── Realized P&L ─────────────────────────────────────────

    def get_realized_pnl(self) -> Decimal:
        result = (
            Trade.objects
            .filter(position__user=self.user,
                    side=Trade.SIDE_SELL,
                    realized_pnl__isnull=False)
            .aggregate(total=Sum("realized_pnl"))
        )
        return result["total"] or Decimal("0")
