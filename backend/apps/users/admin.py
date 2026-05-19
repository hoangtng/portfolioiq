from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ("email", "is_staff", "created_at")
    search_fields = ("email", "first_name", "last_name")
    ordering      = ("-created_at",)

    # Inherit Django's default fieldsets; append our custom fields
    fieldsets = BaseUserAdmin.fieldsets + (
        ("PortfolioIQ", {"fields": ("avatar_url", "bio", "telegram_chat_id")}),
    )
