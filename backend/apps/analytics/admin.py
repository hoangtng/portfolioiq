from django.contrib import admin

from apps.portfolio.models_snapshot import PortfolioSnapshot, PositionSnapshot


@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display  = ("user", "date", "total_market_value",
                     "total_unrealized_pnl", "positions_count", "prices_captured")
    list_filter   = ("prices_captured",)
    search_fields = ("user__email",)
    readonly_fields = ("created_at",)
    ordering = ("-date",)


@admin.register(PositionSnapshot)
class PositionSnapshotAdmin(admin.ModelAdmin):
    list_display  = ("user", "ticker", "asset_type", "date",
                     "price", "market_value", "unrealized_pnl")
    list_filter   = ("asset_type",)
    search_fields = ("ticker", "user__email")
    ordering = ("-date",)
