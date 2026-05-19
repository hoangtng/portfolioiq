"""
AnalyticsService — Phase 3 business logic (fixed).

Methods:
  take_snapshot()           Capture today's portfolio state (idempotent)
  get_pnl_history()         Daily P&L curve for charting
  get_performance_stats()   Win rate, avg win/loss, profit factor, best/worst day
  get_top_performers()      Best (winners) and worst (losers) open positions
  get_asset_allocation()    Breakdown by type and ticker
  get_realized_summary()    Realized P&L by ticker and month

Bug fixes vs. original:
  - best_day / worst_day now compute day-over-day deltas (not lifetime
    cumulative max/min)
  - take_snapshot batches Redis fetches via get_many (was N+1)
  - take_snapshot tracks prices_captured honestly across the per-position
    loop (was lying when summary was complete but per-position failed)
  - take_snapshot isolates per-position errors so one bad row doesn't
    nuke the whole snapshot
  - get_top_performers separates winners from losers — "worst" returns
    only actual losing positions, empty list if everyone is up
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum

from apps.portfolio.models import Position, Trade
from apps.portfolio.models_snapshot import PortfolioSnapshot, PositionSnapshot
from apps.portfolio.services.cache import QuoteCache
from apps.portfolio.services.portfolio import PortfolioService

logger = logging.getLogger(__name__)


class AnalyticsService:

    def __init__(self, user):
        self.user      = user
        self.cache     = QuoteCache()
        self.portfolio = PortfolioService(user)

    # ─── Snapshot ─────────────────────────────────────────────

    def take_snapshot(self) -> tuple[PortfolioSnapshot | None, bool]:
        """
        Capture today's portfolio state. Idempotent — returns the existing
        row if one already exists for today.

        Returns (snapshot, created):
          - (PortfolioSnapshot, True)  — new snapshot
          - (PortfolioSnapshot, False) — already existed today
          - (None, False)              — user has no open positions
        """
        today = date.today()

        existing = PortfolioSnapshot.objects.filter(user=self.user, date=today).first()
        if existing:
            logger.info("Snapshot already exists for %s on %s", self.user.email, today)
            return existing, False

        summary = self.portfolio.get_summary()
        if summary["positions_count"] == 0:
            return None, False

        realized = self.portfolio.get_realized_pnl()

        snapshot = PortfolioSnapshot.objects.create(
            user                     = self.user,
            date                     = today,
            total_cost_basis         = summary["total_cost_basis"],
            total_market_value       = summary["total_market_value"],
            total_unrealized_pnl     = summary["total_unrealized_pnl"],
            total_unrealized_pnl_pct = summary["total_unrealized_pnl_pct"],
            total_realized_pnl       = realized,
            positions_count          = summary["positions_count"],
            prices_captured          = False,  # set True below only if all positions captured
        )

        # Batch fetch all quotes in one Redis roundtrip (was N+1)
        tickers = list({p.ticker for p in summary["positions"]})
        quotes  = self.cache.get_many(tickers) if tickers else {}

        captured_all = True

        for position in summary["positions"]:
            try:
                quote = quotes.get(position.ticker)
                if not quote:
                    captured_all = False
                    continue

                price        = Decimal(str(quote["price"]))
                market_value = position.market_value(price)

                PositionSnapshot.objects.get_or_create(
                    user       = self.user,
                    date       = today,
                    ticker     = position.ticker,
                    asset_type = position.asset_type,
                    defaults=dict(
                        portfolio_snapshot = snapshot,
                        quantity           = position.quantity,
                        avg_cost           = position.avg_cost,
                        price              = price,
                        market_value       = market_value,
                        cost_basis         = position.cost_basis,
                        unrealized_pnl     = position.unrealized_pnl(price),
                        unrealized_pnl_pct = position.unrealized_pnl_pct(price),
                    ),
                )
            except Exception:
                # One bad position shouldn't kill the whole snapshot —
                # the parent row already exists; just log and continue.
                logger.exception(
                    "Position snapshot failed: user=%s ticker=%s date=%s",
                    self.user.email, position.ticker, today,
                )
                captured_all = False

        if captured_all:
            snapshot.prices_captured = True
            snapshot.save(update_fields=["prices_captured"])

        logger.info(
            "Snapshot taken for %s on %s — $%s (%d positions, captured_all=%s)",
            self.user.email, today, snapshot.total_market_value,
            snapshot.positions_count, captured_all,
        )
        return snapshot, True

    # ─── P&L history ──────────────────────────────────────────

    def get_pnl_history(self, days: int = 90) -> list[dict]:
        since = date.today() - timedelta(days=days - 1)
        snapshots = (
            PortfolioSnapshot.objects
            .filter(user=self.user, date__gte=since)
            .order_by("date")
        )

        return [
            {
                "date":                     str(s.date),
                "total_market_value":       float(s.total_market_value),
                "total_unrealized_pnl":     float(s.total_unrealized_pnl),
                "total_unrealized_pnl_pct": float(s.total_unrealized_pnl_pct),
                "total_realized_pnl":       float(s.total_realized_pnl),
            }
            for s in snapshots
        ]

    # ─── Performance stats ────────────────────────────────────

    def get_performance_stats(self) -> dict:
        sells = Trade.objects.filter(
            position__user=self.user, side="sell",
            realized_pnl__isnull=False,
        )

        agg = sells.aggregate(
            total_count  = Count("id"),
            win_count    = Count("id", filter=Q(realized_pnl__gt=0)),
            loss_count   = Count("id", filter=Q(realized_pnl__lt=0)),
            avg_win      = Avg("realized_pnl",  filter=Q(realized_pnl__gt=0)),
            avg_loss     = Avg("realized_pnl",  filter=Q(realized_pnl__lt=0)),
            total_realized = Sum("realized_pnl"),
            gross_profit = Sum("realized_pnl",  filter=Q(realized_pnl__gt=0)),
            gross_loss   = Sum("realized_pnl",  filter=Q(realized_pnl__lt=0)),
        )

        total_count = agg["total_count"]
        win_count   = agg["win_count"]
        loss_count  = agg["loss_count"]
        win_rate    = round((win_count / total_count * 100), 1) if total_count else 0.0

        avg_win        = agg["avg_win"]      or Decimal("0")
        avg_loss       = agg["avg_loss"]     or Decimal("0")
        total_realized = agg["total_realized"] or Decimal("0")
        gross_profit   = agg["gross_profit"] or Decimal("0")
        gross_loss     = abs(agg["gross_loss"] or Decimal("0"))
        profit_factor  = round(float(gross_profit / gross_loss), 2) if gross_loss else None

        best_day, worst_day = self._best_and_worst_days()
        summary = self.portfolio.get_summary()

        return {
            "total_trades":         total_count,
            "win_count":            win_count,
            "loss_count":           loss_count,
            "win_rate":             win_rate,
            "avg_win":              float(avg_win),
            "avg_loss":             float(avg_loss),
            "profit_factor":        profit_factor,
            "total_realized_pnl":   float(total_realized),
            "total_unrealized_pnl": float(summary["total_unrealized_pnl"]),
            "total_pnl":            float(total_realized + summary["total_unrealized_pnl"]),
            "best_day":             best_day,
            "worst_day":            worst_day,
        }

    def _best_and_worst_days(self) -> tuple[dict, dict]:
        """
        Compute day-over-day equity change across consecutive snapshots.
        Returns (best_day, worst_day) where each is {"date", "value"}
        with the date of the biggest gain / loss day.

        With fewer than 2 snapshots, returns (None, None) for both.
        """
        snapshots = list(
            PortfolioSnapshot.objects
            .filter(user=self.user)
            .order_by("date")
            .values("date", "total_market_value", "total_realized_pnl")
        )
        empty = {"date": None, "value": None}
        if len(snapshots) < 2:
            return empty, empty

        deltas: list[tuple[date, Decimal]] = []
        for prev, curr in zip(snapshots, snapshots[1:]):
            # Day's equity change = change in market value + change in
            # realized (since stored realized is cumulative, the diff
            # is what closed that day)
            change = (
                (curr["total_market_value"] - prev["total_market_value"])
                + (curr["total_realized_pnl"] - prev["total_realized_pnl"])
            )
            deltas.append((curr["date"], change))

        best  = max(deltas, key=lambda x: x[1])
        worst = min(deltas, key=lambda x: x[1])
        return (
            {"date": str(best[0]),  "value": float(best[1])},
            {"date": str(worst[0]), "value": float(worst[1])},
        )

    # ─── Top performers ───────────────────────────────────────

    def get_top_performers(self, limit: int = 5) -> dict:
        """
        Returns {"best": [winners], "worst": [losers]}.

        Winners are positions with pnl > 0, sorted by pnl descending.
        Losers are positions with pnl < 0, sorted by pnl ascending
        (most negative first).

        If everyone's up, "worst" is empty rather than including
        marginally profitable positions.
        """
        positions = list(Position.objects.filter(user=self.user, is_open=True))
        if not positions:
            return {"best": [], "worst": []}

        tickers = list({p.ticker for p in positions})
        quotes  = self.cache.get_many(tickers)

        enriched = []
        for p in positions:
            quote = quotes.get(p.ticker)
            if not quote:
                continue
            price        = Decimal(str(quote["price"]))
            market_value = p.market_value(price)

            enriched.append({
                "id":           p.id,
                "ticker":       p.ticker,
                "asset_type":   p.asset_type,
                "pnl":          float(p.unrealized_pnl(price)),
                "pnl_pct":      float(p.unrealized_pnl_pct(price)),
                "market_value": float(market_value),
                "strike":       float(p.strike) if p.strike else None,
                "expiry":       p.expiry.isoformat() if p.expiry else None,
            })

        winners = sorted(
            [p for p in enriched if p["pnl"] > 0],
            key=lambda x: x["pnl"], reverse=True,
        )
        losers = sorted(
            [p for p in enriched if p["pnl"] < 0],
            key=lambda x: x["pnl"],   # most negative first
        )

        return {
            "best":  winners[:limit],
            "worst": losers[:limit],
        }

    # ─── Asset allocation ─────────────────────────────────────

    def get_asset_allocation(self) -> dict:
        positions = list(Position.objects.filter(user=self.user, is_open=True))
        if not positions:
            return {"total_value": 0.0, "by_type": [], "by_ticker": []}

        tickers = list({p.ticker for p in positions})
        quotes  = self.cache.get_many(tickers)

        total_value: Decimal           = Decimal("0")
        by_type:   dict[str, Decimal]  = {}
        by_ticker: dict[str, Decimal]  = {}

        for p in positions:
            quote = quotes.get(p.ticker)
            # Fall back to avg cost if no live price — cost basis is
            # better than zero for allocation %.
            price        = Decimal(str(quote["price"])) if quote else p.avg_cost
            market_value = p.market_value(price)

            total_value += market_value
            by_type[p.asset_type] = by_type.get(p.asset_type, Decimal("0")) + market_value
            by_ticker[p.ticker]   = by_ticker.get(p.ticker,   Decimal("0")) + market_value

        def to_pct_list(d: dict[str, Decimal]) -> list[dict]:
            return sorted(
                [
                    {
                        "name":  k,
                        "value": float(v),
                        "pct":   round(float(v / total_value * 100), 1) if total_value else 0,
                    }
                    for k, v in d.items()
                ],
                key=lambda x: x["value"],
                reverse=True,
            )

        return {
            "total_value": float(total_value),
            "by_type":     to_pct_list(by_type),
            "by_ticker":   to_pct_list(by_ticker),
        }

    # ─── Realized summary ─────────────────────────────────────

    def get_realized_summary(self) -> dict:
        sells = (
            Trade.objects
            .filter(position__user=self.user, side="sell", realized_pnl__isnull=False)
            .select_related("position")
        )

        by_ticker: dict[str, Decimal] = {}
        by_month:  dict[str, Decimal] = {}

        for trade in sells:
            ticker = trade.position.ticker
            month  = trade.executed_at.strftime("%Y-%m")
            pnl    = trade.realized_pnl or Decimal("0")
            by_ticker[ticker] = by_ticker.get(ticker, Decimal("0")) + pnl
            by_month[month]   = by_month.get(month, Decimal("0")) + pnl

        total = sum(by_ticker.values(), Decimal("0"))

        return {
            "total_realized_pnl": float(total),
            "by_ticker": sorted(
                [{"ticker": k, "pnl": float(v)} for k, v in by_ticker.items()],
                key=lambda x: x["pnl"], reverse=True,
            ),
            "by_month": [
                {"month": k, "pnl": float(v)}
                for k, v in sorted(by_month.items())
            ],
        }
