"""
Serializers for analytics endpoints. Most are plain Serializer (not
ModelSerializer) because the data is computed, not stored.

Bug fixes vs. original:
  - date is DateField, not CharField — gives proper validation and
    consistent ISO-8601 formatting.
"""

from rest_framework import serializers

from apps.portfolio.models_snapshot import PortfolioSnapshot


class PortfolioSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PortfolioSnapshot
        fields = (
            "id", "date",
            "total_cost_basis", "total_market_value",
            "total_unrealized_pnl", "total_unrealized_pnl_pct",
            "total_realized_pnl", "positions_count", "prices_captured",
            "created_at",
        )


class PnLHistoryItemSerializer(serializers.Serializer):
    date                     = serializers.DateField()
    total_market_value       = serializers.FloatField()
    total_unrealized_pnl     = serializers.FloatField()
    total_unrealized_pnl_pct = serializers.FloatField()
    total_realized_pnl       = serializers.FloatField()


class PnLHistoryResponseSerializer(serializers.Serializer):
    days    = serializers.IntegerField()
    count   = serializers.IntegerField()
    history = PnLHistoryItemSerializer(many=True)


class _DayValueSerializer(serializers.Serializer):
    date  = serializers.DateField(allow_null=True)
    value = serializers.FloatField(allow_null=True)


class PerformanceStatsSerializer(serializers.Serializer):
    total_trades         = serializers.IntegerField()
    win_count            = serializers.IntegerField()
    loss_count           = serializers.IntegerField()
    win_rate             = serializers.FloatField()
    avg_win              = serializers.FloatField()
    avg_loss             = serializers.FloatField()
    profit_factor        = serializers.FloatField(allow_null=True)
    total_realized_pnl   = serializers.FloatField()
    total_unrealized_pnl = serializers.FloatField()
    total_pnl            = serializers.FloatField()
    best_day             = _DayValueSerializer()
    worst_day            = _DayValueSerializer()


class PerformerSerializer(serializers.Serializer):
    id           = serializers.IntegerField()
    ticker       = serializers.CharField()
    asset_type   = serializers.CharField()
    pnl          = serializers.FloatField()
    pnl_pct      = serializers.FloatField()
    market_value = serializers.FloatField()
    strike       = serializers.FloatField(allow_null=True)
    expiry       = serializers.DateField(allow_null=True)


class TopPerformersSerializer(serializers.Serializer):
    best  = PerformerSerializer(many=True)
    worst = PerformerSerializer(many=True)


class AllocationItemSerializer(serializers.Serializer):
    name  = serializers.CharField()
    value = serializers.FloatField()
    pct   = serializers.FloatField()


class AssetAllocationSerializer(serializers.Serializer):
    total_value = serializers.FloatField()
    by_type     = AllocationItemSerializer(many=True)
    by_ticker   = AllocationItemSerializer(many=True)


class _RealizedTickerSerializer(serializers.Serializer):
    ticker = serializers.CharField()
    pnl    = serializers.FloatField()


class _RealizedMonthSerializer(serializers.Serializer):
    month = serializers.CharField()
    pnl   = serializers.FloatField()


class RealizedSummarySerializer(serializers.Serializer):
    total_realized_pnl = serializers.FloatField()
    by_ticker          = _RealizedTickerSerializer(many=True)
    by_month           = _RealizedMonthSerializer(many=True)
