"""
Phase 3 tests — analytics service, API endpoints, Celery task.
Uses shared conftest.py fixtures: client, user, auth_headers.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest


# ─── Local fixtures ──────────────────────────────────────────

@pytest.fixture
def stock_position(db, user):
    from apps.portfolio.models import Position
    return Position.objects.create(
        user=user, ticker="NVDA", asset_type="stock",
        quantity=Decimal("10"), avg_cost=Decimal("820.00"),
    )


@pytest.fixture
def option_position(db, user):
    from apps.portfolio.models import Position
    return Position.objects.create(
        user=user, ticker="PLTR", asset_type="call",
        quantity=Decimal("2"), avg_cost=Decimal("4.50"),
        strike=Decimal("160.00"), expiry="2025-07-18",
    )


@pytest.fixture
def closed_winning_trade(db, user):
    from apps.portfolio.models import Position, Trade

    pos = Position.objects.create(
        user=user, ticker="AAPL", asset_type="stock",
        quantity=Decimal("0"), avg_cost=Decimal("170.00"), is_open=False,
    )
    Trade.objects.create(
        position=pos, side="buy",
        quantity=Decimal("5"), price=Decimal("170.00"),
        executed_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
    )
    Trade.objects.create(
        position=pos, side="sell",
        quantity=Decimal("5"), price=Decimal("190.00"),
        realized_pnl=Decimal("100.00"),
        executed_at=datetime(2025, 2, 14, tzinfo=timezone.utc),
    )
    return pos


@pytest.fixture
def existing_snapshot(db, user):
    from apps.portfolio.models_snapshot import PortfolioSnapshot
    return PortfolioSnapshot.objects.create(
        user=user, date=date.today(),
        total_cost_basis=Decimal("8200.00"),
        total_market_value=Decimal("8780.00"),
        total_unrealized_pnl=Decimal("580.00"),
        total_unrealized_pnl_pct=Decimal("7.07"),
        total_realized_pnl=Decimal("100.00"),
        positions_count=1,
        prices_captured=True,
    )


# ─── take_snapshot ───────────────────────────────────────────

@pytest.mark.django_db
class TestTakeSnapshot:

    def test_creates_snapshot(self, user, stock_position):
        from apps.analytics.services import AnalyticsService

        with patch("apps.analytics.services.QuoteCache.get_many",
                   return_value={"NVDA": {"price": 878.0}}), \
             patch("apps.analytics.services.QuoteCache.get",
                   return_value={"price": 878.0}):
            snapshot = AnalyticsService(user).take_snapshot()

        assert snapshot is not None
        assert snapshot.date == date.today()
        assert snapshot.positions_count == 1
        assert float(snapshot.total_market_value) == 8780.0

    def test_creates_position_snapshots(self, user, stock_position):
        from apps.analytics.services import AnalyticsService
        from apps.portfolio.models_snapshot import PositionSnapshot

        with patch("apps.analytics.services.QuoteCache.get_many",
                   return_value={"NVDA": {"price": 878.0}}), \
             patch("apps.analytics.services.QuoteCache.get",
                   return_value={"price": 878.0}):
            AnalyticsService(user).take_snapshot()

        ps = PositionSnapshot.objects.filter(user=user)
        assert ps.count() == 1
        assert ps.first().ticker == "NVDA"

    def test_idempotent(self, user, stock_position, existing_snapshot):
        from apps.analytics.services import AnalyticsService
        from apps.portfolio.models_snapshot import PortfolioSnapshot

        before = PortfolioSnapshot.objects.filter(user=user).count()
        with patch("apps.analytics.services.QuoteCache.get_many", return_value={}):
            result = AnalyticsService(user).take_snapshot()

        assert result.id == existing_snapshot.id
        assert PortfolioSnapshot.objects.filter(user=user).count() == before

    def test_empty_portfolio_returns_none(self, user):
        from apps.analytics.services import AnalyticsService
        assert AnalyticsService(user).take_snapshot() is None


# ─── P&L history ──────────────────────────────────────────────

@pytest.mark.django_db
class TestPnLHistory:

    def test_returns_snapshots_in_date_order(self, user):
        from apps.analytics.services import AnalyticsService
        from apps.portfolio.models_snapshot import PortfolioSnapshot

        today = date.today()
        for i in range(5):
            PortfolioSnapshot.objects.create(
                user=user,
                date=today - timedelta(days=i),
                total_cost_basis=Decimal("8000"),
                total_market_value=Decimal("8000") + Decimal(str(i * 100)),
                total_unrealized_pnl=Decimal(str(i * 100)),
                total_unrealized_pnl_pct=Decimal(str(i * 1.25)),
                total_realized_pnl=Decimal("0"),
                positions_count=1,
            )

        history = AnalyticsService(user).get_pnl_history(days=7)
        assert len(history) == 5
        assert history[0]["date"] < history[-1]["date"]

    def test_respects_days_filter(self, user):
        from apps.analytics.services import AnalyticsService
        from apps.portfolio.models_snapshot import PortfolioSnapshot

        today = date.today()
        for i in range(60):
            PortfolioSnapshot.objects.create(
                user=user,
                date=today - timedelta(days=i),
                total_cost_basis=Decimal("8000"),
                total_market_value=Decimal("8500"),
                total_unrealized_pnl=Decimal("500"),
                total_unrealized_pnl_pct=Decimal("6.25"),
                total_realized_pnl=Decimal("0"),
                positions_count=1,
            )

        assert len(AnalyticsService(user).get_pnl_history(days=30)) == 30

    def test_empty_returns_empty_list(self, user):
        from apps.analytics.services import AnalyticsService
        assert AnalyticsService(user).get_pnl_history() == []


# ─── Performance stats ────────────────────────────────────────

@pytest.mark.django_db
class TestPerformanceStats:

    def test_win_rate(self, user, closed_winning_trade):
        from apps.analytics.services import AnalyticsService
        with patch("apps.analytics.services.QuoteCache.get_many", return_value={}):
            stats = AnalyticsService(user).get_performance_stats()
        assert stats["total_trades"] == 1
        assert stats["win_count"]    == 1
        assert stats["win_rate"]     == 100.0

    def test_total_realized_pnl(self, user, closed_winning_trade):
        from apps.analytics.services import AnalyticsService
        with patch("apps.analytics.services.QuoteCache.get_many", return_value={}):
            stats = AnalyticsService(user).get_performance_stats()
        assert stats["total_realized_pnl"] == 100.0

    def test_empty(self, user):
        from apps.analytics.services import AnalyticsService
        with patch("apps.analytics.services.QuoteCache.get_many", return_value={}):
            stats = AnalyticsService(user).get_performance_stats()
        assert stats["total_trades"]  == 0
        assert stats["win_rate"]      == 0.0
        assert stats["profit_factor"] is None


# ─── Top performers ───────────────────────────────────────────

@pytest.mark.django_db
class TestTopPerformers:

    def test_returns_best_and_worst(self, user, stock_position, option_position):
        from apps.analytics.services import AnalyticsService
        mock_quotes = {
            "NVDA": {"price": 878.0},   # winner
            "PLTR": {"price": 3.0},     # loser
        }
        with patch("apps.analytics.services.QuoteCache.get_many",
                   return_value=mock_quotes):
            result = AnalyticsService(user).get_top_performers(limit=5)

        assert result["best"][0]["ticker"]  == "NVDA"
        assert result["worst"][0]["ticker"] == "PLTR"

    def test_empty_portfolio(self, user):
        from apps.analytics.services import AnalyticsService
        with patch("apps.analytics.services.QuoteCache.get_many", return_value={}):
            assert AnalyticsService(user).get_top_performers() == {"best": [], "worst": []}


# ─── Asset allocation ─────────────────────────────────────────

@pytest.mark.django_db
class TestAssetAllocation:

    def test_includes_both_types(self, user, stock_position, option_position):
        from apps.analytics.services import AnalyticsService
        mock_quotes = {
            "NVDA": {"price": 878.0},
            "PLTR": {"price": 5.0},
        }
        with patch("apps.analytics.services.QuoteCache.get_many",
                   return_value=mock_quotes):
            result = AnalyticsService(user).get_asset_allocation()

        types = {item["name"] for item in result["by_type"]}
        assert types == {"stock", "call"}
        assert abs(sum(item["pct"] for item in result["by_type"]) - 100.0) < 0.5

    def test_empty(self, user):
        from apps.analytics.services import AnalyticsService
        result = AnalyticsService(user).get_asset_allocation()
        assert result["by_type"]   == []
        assert result["by_ticker"] == []


# ─── Realized summary ─────────────────────────────────────────

@pytest.mark.django_db
class TestRealizedSummary:

    def test_groups_by_ticker_and_month(self, user, closed_winning_trade):
        from apps.analytics.services import AnalyticsService
        result = AnalyticsService(user).get_realized_summary()

        assert result["total_realized_pnl"] == 100.0
        tickers = [x["ticker"] for x in result["by_ticker"]]
        assert "AAPL" in tickers
        assert len(result["by_month"]) >= 1

    def test_empty(self, user):
        from apps.analytics.services import AnalyticsService
        result = AnalyticsService(user).get_realized_summary()
        assert result["total_realized_pnl"] == 0.0
        assert result["by_ticker"] == []


# ─── HTTP endpoints ───────────────────────────────────────────

@pytest.mark.django_db
class TestAnalyticsAPI:

    def test_history_requires_auth(self, client):
        assert client.get("/api/analytics/history/").status_code == 401

    def test_history_empty(self, client, auth_headers):
        resp = client.get("/api/analytics/history/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"]   == 0
        assert resp.json()["history"] == []

    def test_history_days_param(self, client, auth_headers):
        resp = client.get("/api/analytics/history/?days=30", **auth_headers)
        assert resp.json()["days"] == 30

    def test_stats_returns_structure(self, client, auth_headers):
        with patch("apps.analytics.services.QuoteCache.get_many", return_value={}):
            resp = client.get("/api/analytics/stats/", **auth_headers)
        assert resp.status_code == 200
        for key in ("win_rate", "total_trades", "profit_factor",
                    "best_day", "worst_day"):
            assert key in resp.json()

    def test_performers_empty(self, client, auth_headers):
        with patch("apps.analytics.services.QuoteCache.get_many", return_value={}):
            resp = client.get("/api/analytics/performers/", **auth_headers)
        assert resp.json() == {"best": [], "worst": []}

    def test_allocation_empty(self, client, auth_headers):
        resp = client.get("/api/analytics/allocation/", **auth_headers)
        assert resp.json()["by_type"] == []

    def test_realized_returns_structure(self, client, auth_headers):
        resp = client.get("/api/analytics/realized/", **auth_headers)
        data = resp.json()
        assert "total_realized_pnl" in data
        assert "by_ticker"          in data
        assert "by_month"           in data

    def test_snapshot_trigger(self, client, auth_headers, stock_position):
        with patch("apps.analytics.services.QuoteCache.get_many",
                   return_value={"NVDA": {"price": 878.0}}), \
             patch("apps.analytics.services.QuoteCache.get",
                   return_value={"price": 878.0}):
            resp = client.post(
                "/api/analytics/snapshot/",
                content_type="application/json",
                **auth_headers,
            )
        assert resp.status_code == 201
        assert resp.json()["positions_count"] == 1

    def test_snapshot_empty_portfolio(self, client, auth_headers):
        resp = client.post(
            "/api/analytics/snapshot/",
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        assert "No open positions" in resp.json()["message"]


# ─── Celery task ──────────────────────────────────────────────

@pytest.mark.django_db
class TestCelerySnapshotTask:

    def test_takes_snapshot_for_users_with_positions(self, user, stock_position):
        from apps.analytics.tasks import take_portfolio_snapshot
        with patch("apps.analytics.services.QuoteCache.get_many",
                   return_value={"NVDA": {"price": 878.0}}), \
             patch("apps.analytics.services.QuoteCache.get",
                   return_value={"price": 878.0}):
            result = take_portfolio_snapshot()

        assert result["taken"]  == 1
        assert result["errors"] == 0

    def test_skips_when_no_users_have_positions(self, user):
        from apps.analytics.tasks import take_portfolio_snapshot
        result = take_portfolio_snapshot()
        assert result["taken"]   == 0
        assert result["skipped"] == 0
