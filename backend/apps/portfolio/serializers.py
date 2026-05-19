"""
Serializers for the portfolio app.

PositionSerializer is the most interesting one — it enriches static
Postgres data with live Redis prices via SerializerMethodField.
"""

from decimal import Decimal

from rest_framework import serializers

from .models import PriceAlert, Position, Trade, Watchlist
from .services.cache import QuoteCache


# ─── Watchlist ────────────────────────────────────────────────

class WatchlistSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Watchlist
        fields = ("id", "ticker", "notes", "added_at")
        read_only_fields = ("id", "added_at")

    def validate_ticker(self, value: str) -> str:
        return value.upper().strip()


# ─── Trade ────────────────────────────────────────────────────

class TradeSerializer(serializers.ModelSerializer):
    total_value = serializers.DecimalField(max_digits=14, decimal_places=4,
                                            read_only=True)

    class Meta:
        model  = Trade
        fields = ("id", "side", "quantity", "price", "fees",
                  "executed_at", "realized_pnl", "notes", "total_value",
                  "created_at")
        read_only_fields = ("id", "realized_pnl", "total_value", "created_at")


# ─── Position ─────────────────────────────────────────────────

class PositionSerializer(serializers.ModelSerializer):
    """
    Position with live price enrichment from Redis.
    On cache miss, current_price/unrealized_pnl/market_value are null.
    """
    trades       = TradeSerializer(many=True, read_only=True)
    cost_basis   = serializers.DecimalField(max_digits=14, decimal_places=4,
                                             read_only=True)

    current_price       = serializers.SerializerMethodField()
    unrealized_pnl      = serializers.SerializerMethodField()
    unrealized_pnl_pct  = serializers.SerializerMethodField()
    market_value        = serializers.SerializerMethodField()

    class Meta:
        model  = Position
        fields = ("id", "ticker", "asset_type", "quantity", "avg_cost",
                  "strike", "expiry", "is_open", "opened_at", "closed_at",
                  "cost_basis", "current_price", "unrealized_pnl",
                  "unrealized_pnl_pct", "market_value", "trades")
        read_only_fields = (
            "id", "opened_at", "closed_at", "cost_basis",
            "current_price", "unrealized_pnl", "unrealized_pnl_pct",
            "market_value", "trades",
        )

    def _get_price(self, obj: Position) -> Decimal | None:
        attr = f"_price_{obj.ticker}"
        if not hasattr(self, attr):
            quote = QuoteCache().get(obj.ticker)
            setattr(self, attr, Decimal(str(quote["price"])) if quote else None)
        return getattr(self, attr)

    def get_current_price(self, obj):
        price = self._get_price(obj)
        return str(price) if price is not None else None

    def get_unrealized_pnl(self, obj):
        price = self._get_price(obj)
        return str(obj.unrealized_pnl(price)) if price is not None else None

    def get_unrealized_pnl_pct(self, obj):
        price = self._get_price(obj)
        return str(round(obj.unrealized_pnl_pct(price), 2)) if price is not None else None

    def get_market_value(self, obj):
        price = self._get_price(obj)
        return str(obj.market_value(price)) if price is not None else None


class PositionCreateSerializer(serializers.ModelSerializer):
    """Simpler serializer for POST. No enriched fields, no nested trades."""

    class Meta:
        model  = Position
        fields = ("id", "ticker", "asset_type", "quantity", "avg_cost",
                  "strike", "expiry")
        read_only_fields = ("id",)

    def validate_ticker(self, value: str) -> str:
        return value.upper().strip()

    def validate(self, attrs):
        asset_type = attrs.get("asset_type", Position.ASSET_STOCK)
        if asset_type in (Position.ASSET_CALL, Position.ASSET_PUT):
            if not attrs.get("strike"):
                raise serializers.ValidationError(
                    {"strike": "Strike price is required for options."}
                )
            if not attrs.get("expiry"):
                raise serializers.ValidationError(
                    {"expiry": "Expiry date is required for options."}
                )
        return attrs


# ─── Portfolio summary ────────────────────────────────────────

class PortfolioSummarySerializer(serializers.Serializer):
    """Aggregate view — not backed by a model."""
    total_cost_basis           = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_market_value         = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_unrealized_pnl       = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_unrealized_pnl_pct   = serializers.DecimalField(max_digits=8,  decimal_places=2)
    positions_count            = serializers.IntegerField()
    positions                  = PositionSerializer(many=True)
    prices_cached              = serializers.BooleanField()


# ─── Price alert ──────────────────────────────────────────────

class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PriceAlert
        fields = ("id", "ticker", "condition", "target_price", "is_active",
                  "triggered_at", "triggered_price", "created_at")
        read_only_fields = ("id", "triggered_at", "triggered_price", "created_at")

    def validate_ticker(self, value: str) -> str:
        return value.upper().strip()
