from django.contrib import admin

from .models import PriceAlert, Position, Trade, Watchlist


class TradeInline(admin.TabularInline):
    model = Trade
    extra = 0
    readonly_fields = ("realized_pnl", "total_value", "created_at")
    fields = ("side", "quantity", "price", "fees", "executed_at",
              "realized_pnl", "notes", "created_at")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display  = ("ticker", "asset_type", "quantity", "avg_cost",
                     "is_open", "user", "opened_at")
    list_filter   = ("is_open", "asset_type")
    search_fields = ("ticker", "user__email")
    readonly_fields = ("cost_basis_display", "opened_at", "closed_at")
    inlines = [TradeInline]

    def cost_basis_display(self, obj):
        return f"${obj.cost_basis:,.2f}"
    cost_basis_display.short_description = "Cost basis"


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display  = ("__str__", "side", "executed_at", "realized_pnl")
    list_filter   = ("side",)
    search_fields = ("position__ticker",)


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display  = ("ticker", "user", "added_at")
    search_fields = ("ticker", "user__email")


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display  = ("ticker", "condition", "target_price", "is_active",
                     "user", "triggered_at")
    list_filter   = ("is_active", "condition")
    search_fields = ("ticker", "user__email")
