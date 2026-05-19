from django.contrib import admin

from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display    = ("title", "ticker", "ai_generated", "user", "created_at")
    list_filter     = ("ai_generated",)
    search_fields   = ("title", "body", "ticker", "user__email")
    readonly_fields = ("created_at", "updated_at", "trade_id")
    ordering        = ("-created_at",)
