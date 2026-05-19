"""
Phase 1 tests: model math, PortfolioService, API, MassiveClient, Celery tasks.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest


# ─── Local fixtures ───────────────────────────────────────────

@pytest.fixture
def stock_position(db, user):
    from apps.portfolio.models import Position
    return Position.objects.create(
        user=user, ticker="NVDA", asset_type=Position.ASSET_STOCK,
        quantity=Decimal("10"), avg_cost=Decimal("820.00"),
    )


@pytest.fixture
def option_position(db, user):
    from apps.portfolio.models import Position
    return Position.objects.create(
        user=user, ticker="PLTR", asset_type=Position.ASSET_CALL,
        quantity=Decimal("2"), avg_cost=Decimal("4.50"),
        strike=Decimal("160.00"), expiry="2025-07-18",
    )


# ─── Model math ───────────────────────────────────────────────

@pytest.mark.django_db
class TestPositionModel:

    def test_cost_basis_stock(self, stock_position):
        assert stock_position.cost_basis == Decimal("8200.00")

    def test_cost_basis_option_uses_100_multiplier(self, option_position):
        assert option_position.cost_basis == Decimal("900.00")

    def test_unrealized_pnl_profit(self, stock_position):
        assert stock_position.unrealized_pnl(Decimal("878.00")) == Decimal("580.00")

    def test_unrealized_pnl_loss(self, stock_position):
        assert stock_position.unrealized_pnl(Decimal("780.00")) == Decimal("-400.00")

    def test_unrealized_pnl_pct(self, stock_position):
        assert stock_position.unrealized_pnl_pct(Decimal("902.00")) == Decimal("10.00")

    def test_is_option(self, stock_position, option_position):
        assert stock_position.is_option is False
        assert option_position.is_option is True

    def test_contract_multiplier(self, stock_position, option_position):
        assert stock_position.contract_multiplier  == Decimal("1")
        assert option_position.contract_multiplier == Decimal("100")


# ─── PortfolioService ─────────────────────────────────────────

@pytest.mark.django_db
class TestPortfolioService:

    def test_summary_empty(self, user):
        from apps.portfolio.services.portfolio import PortfolioService
        s = PortfolioService(user).get_summary()
        assert s["positions_count"]  == 0
        assert s["total_cost_basis"] == Decimal("0")
        assert s["prices_cached"] is True

    def test_summary_with_prices(self, user, stock_position):
        from apps.portfolio.services.portfolio import PortfolioService
        with patch("apps.portfolio.services.portfolio.QuoteCache.get_many",
                   return_value={"NVDA": {"price": 878.0}}):
            s = PortfolioService(user).get_summary()
        assert s["total_market_value"]   == Decimal("8780.00")
        assert s["total_unrealized_pnl"] == Decimal("580.00")
        assert s["prices_cached"] is True

    def test_summary_marks_uncached(self, user, stock_position):
        from apps.portfolio.services.portfolio import PortfolioService
        with patch("apps.portfolio.services.portfolio.QuoteCache.get_many",
                   return_value={}):
            s = PortfolioService(user).get_summary()
        assert s["prices_cached"] is False

    def test_record_buy_updates_avg_cost(self, user, stock_position):
        from apps.portfolio.services.portfolio import PortfolioService
        from apps.portfolio.models import Trade

        PortfolioService(user).record_trade(
            position=stock_position, side=Trade.SIDE_BUY,
            quantity=Decimal("10"), price=Decimal("900.00"),
        )
        stock_position.refresh_from_db()
        assert stock_position.quantity == Decimal("20")
        assert stock_position.avg_cost == Decimal("860.00")

    def test_record_sell_calculates_pnl(self, user, stock_position):
        from apps.portfolio.services.portfolio import PortfolioService
        from apps.portfolio.models import Trade

        trade = PortfolioService(user).record_trade(
            position=stock_position, side=Trade.SIDE_SELL,
            quantity=Decimal("5"), price=Decimal("900.00"),
        )
        assert trade.realized_pnl == Decimal("400.00")

    def test_sell_all_closes_position(self, user, stock_position):
        from apps.portfolio.services.portfolio import PortfolioService
        from apps.portfolio.models import Trade

        PortfolioService(user).record_trade(
            position=stock_position, side=Trade.SIDE_SELL,
            quantity=Decimal("10"), price=Decimal("900.00"),
        )
        stock_position.refresh_from_db()
        assert stock_position.quantity  == Decimal("0")
        assert stock_position.is_open   is False
        assert stock_position.closed_at is not None

    def test_oversell_raises(self, user, stock_position):
        from apps.portfolio.services.portfolio import PortfolioService
        from apps.portfolio.models import Trade

        with pytest.raises(ValueError, match="Cannot sell"):
            PortfolioService(user).record_trade(
                position=stock_position, side=Trade.SIDE_SELL,
                quantity=Decimal("999"), price=Decimal("900.00"),
            )


# ─── API endpoints ────────────────────────────────────────────

@pytest.mark.django_db
class TestPortfolioAPI:

    def test_summary_requires_auth(self, client):
        assert client.get("/api/portfolio/summary/").status_code == 401

    def test_summary_empty_portfolio(self, client, auth_headers):
        with patch("apps.portfolio.services.portfolio.QuoteCache.get_many",
                   return_value={}):
            resp = client.get("/api/portfolio/summary/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["positions_count"] == 0

    def test_create_stock_position(self, client, auth_headers):
        resp = client.post(
            "/api/portfolio/positions/",
            {"ticker": "aapl", "asset_type": "stock",
             "quantity": "10", "avg_cost": "175.00"},
            content_type="application/json", **auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["ticker"] == "AAPL"

    def test_create_option_position(self, client, auth_headers):
        resp = client.post(
            "/api/portfolio/positions/",
            {"ticker": "PLTR", "asset_type": "call", "quantity": "2",
             "avg_cost": "4.50", "strike": "160.00", "expiry": "2025-07-18"},
            content_type="application/json", **auth_headers,
        )
        assert resp.status_code == 201

    def test_create_option_without_strike_fails(self, client, auth_headers):
        resp = client.post(
            "/api/portfolio/positions/",
            {"ticker": "PLTR", "asset_type": "call",
             "quantity": "2", "avg_cost": "4.50"},
            content_type="application/json", **auth_headers,
        )
        assert resp.status_code == 400

    def test_list_positions(self, client, auth_headers, stock_position):
        resp = client.get("/api/portfolio/positions/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_record_trade_via_api(self, client, auth_headers, stock_position):
        resp = client.post(
            f"/api/portfolio/positions/{stock_position.id}/trades/",
            {"side": "buy", "quantity": "5", "price": "900",
             "executed_at": "2025-01-01T12:00:00Z"},
            content_type="application/json", **auth_headers,
        )
        assert resp.status_code == 201
        stock_position.refresh_from_db()
        assert stock_position.quantity == Decimal("15")

    def test_create_alert(self, client, auth_headers):
        resp = client.post(
            "/api/portfolio/alerts/",
            {"ticker": "PLTR", "condition": "above", "target_price": "30.00"},
            content_type="application/json", **auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["is_active"] is True

    def test_watchlist_add_and_list(self, client, auth_headers):
        client.post(
            "/api/portfolio/watchlist/",
            {"ticker": "tsla", "notes": "Watching"},
            content_type="application/json", **auth_headers,
        )
        resp = client.get("/api/portfolio/watchlist/", **auth_headers)
        assert resp.json()["results"][0]["ticker"] == "TSLA"

    def test_quote_view_paid_plan(self, client, auth_headers):
        mock_quotes = {"PLTR": {"price": 23.45, "change_pct": 1.5}}
        with patch("apps.portfolio.views.MassiveClient.get_snapshot",
                   return_value=mock_quotes):
            resp = client.get("/api/portfolio/quote/PLTR/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["price"] == 23.45

    def test_quote_view_free_tier_fallback(self, client, auth_headers):
        with patch("apps.portfolio.views.MassiveClient.get_snapshot", return_value={}), \
             patch("apps.portfolio.views.MassiveClient.get_previous_close",
                   return_value={"price": 23.45, "change_pct": 0.0}):
            resp = client.get("/api/portfolio/quote/PLTR/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["price"] == 23.45

    def test_quote_view_404(self, client, auth_headers):
        with patch("apps.portfolio.views.MassiveClient.get_snapshot", return_value={}), \
             patch("apps.portfolio.views.MassiveClient.get_previous_close",
                   return_value=None):
            resp = client.get("/api/portfolio/quote/FAKE/", **auth_headers)
        assert resp.status_code == 404


# ─── MassiveClient ────────────────────────────────────────────

class TestMassiveClient:

    def _make(self):
        from apps.portfolio.services.massive import MassiveClient
        return MassiveClient()

    def test_snapshot_parses_response(self):
        mock = {"tickers": [{
            "ticker": "NVDA",
            "day":     {"c": 878.0, "o": 850.0, "h": 890.0, "l": 848.0, "v": 5_000_000},
            "prevDay": {"c": 860.0},
            "todaysChange": 18.0, "todaysChangePerc": 2.09,
        }]}
        c = self._make()
        with patch.object(c, "_get", return_value=mock):
            result = c.get_snapshot(["NVDA"])
        assert result["NVDA"]["price"]      == 878.0
        assert result["NVDA"]["change_pct"] == 2.09

    def test_snapshot_falls_back_to_prevday(self):
        mock = {"tickers": [{
            "ticker": "PLTR",
            "day":     {},
            "prevDay": {"c": 23.45, "o": 22.80, "v": 1_000_000},
            "todaysChange": 0.0, "todaysChangePerc": 0.0,
        }]}
        c = self._make()
        with patch.object(c, "_get", return_value=mock):
            assert c.get_snapshot(["PLTR"])["PLTR"]["price"] == 23.45

    def test_prev_close_parses(self):
        mock = {"results": [{"c": 23.45, "o": 22.80, "h": 24.10,
                              "l": 22.60, "v": 1_234_567, "vw": 23.12}]}
        c = self._make()
        with patch.object(c, "_get", return_value=mock):
            result = c.get_previous_close("PLTR")
        assert result["price"] == 23.45
        assert result["vwap"]  == 23.12

    def test_options_chain_verbose_fields(self):
        mock_raw = [{
            "details": {"ticker": "O:PLTR250718C00160000",
                        "contract_type":   "call",
                        "expiration_date": "2025-07-18",
                        "strike_price":    160.0,
                        "shares_per_contract": 100},
            "day": {"close": 4.50, "open": 4.20, "high": 4.80,
                     "low": 4.10, "volume": 1234, "vwap": 4.45},
            "greeks": {"delta": 0.45, "gamma": 0.03, "theta": -0.05, "vega": 0.12},
            "implied_volatility": 0.68,
            "open_interest": 5678,
            "break_even_price": 164.50,
            "underlying_asset": {"price": 156.80, "ticker": "PLTR"},
        }]
        c = self._make()
        with patch.object(c, "_paginate", return_value=mock_raw):
            contracts = c.get_options_chain("PLTR")
        assert contracts[0]["strike"]     == 160.0
        assert contracts[0]["last_price"] == 4.50
        assert contracts[0]["delta"]      == 0.45

    def test_options_chain_403_returns_empty(self):
        from apps.portfolio.services.massive import MassiveError
        c = self._make()
        with patch.object(c, "_paginate", side_effect=MassiveError("403")):
            assert c.get_options_chain("PLTR") == []


# ─── Celery tasks ─────────────────────────────────────────────

@pytest.mark.django_db
class TestCeleryTasks:

    def test_fetch_quotes_no_tickers(self):
        from apps.portfolio.tasks import fetch_quotes
        assert fetch_quotes()["fetched"] == 0

    def test_fetch_quotes_paid_plan(self, stock_position):
        from apps.portfolio.tasks import fetch_quotes
        mock_quotes = {"NVDA": {"price": 878.0}}
        with patch("apps.portfolio.tasks.MassiveClient.get_snapshot",
                   return_value=mock_quotes) as snap, \
             patch("apps.portfolio.tasks.QuoteCache.set") as cache_set:
            result = fetch_quotes()
        snap.assert_called_once()
        cache_set.assert_called_once_with("NVDA", mock_quotes["NVDA"])
        assert result["fetched"] == 1

    def test_fetch_quotes_free_tier_fallback(self, stock_position):
        from apps.portfolio.tasks import fetch_quotes
        from apps.portfolio.services.massive import MassiveError

        with patch("apps.portfolio.tasks.MassiveClient.get_snapshot",
                   side_effect=MassiveError("403")), \
             patch("apps.portfolio.tasks.MassiveClient.get_previous_close_many",
                   return_value={"NVDA": {"price": 860.0}}) as prev, \
             patch("apps.portfolio.tasks.QuoteCache.set"):
            result = fetch_quotes()
        prev.assert_called_once()
        assert result["fetched"] == 1

    def test_check_alerts_triggers(self, user):
        from apps.portfolio.models import PriceAlert
        from apps.portfolio.tasks import check_price_alerts

        user.telegram_chat_id = "123456"
        user.save()
        PriceAlert.objects.create(
            user=user, ticker="PLTR", condition="above",
            target_price=Decimal("25.00"),
        )
        with patch("apps.portfolio.tasks.QuoteCache.get_many",
                   return_value={"PLTR": {"price": 26.00}}):
            result = check_price_alerts()
        assert result["triggered"] == 1

    def test_check_alerts_no_trigger(self, user):
        from apps.portfolio.models import PriceAlert
        from apps.portfolio.tasks import check_price_alerts

        PriceAlert.objects.create(
            user=user, ticker="PLTR", condition="above",
            target_price=Decimal("50.00"),
        )
        with patch("apps.portfolio.tasks.QuoteCache.get_many",
                   return_value={"PLTR": {"price": 26.00}}):
            assert check_price_alerts()["triggered"] == 0
