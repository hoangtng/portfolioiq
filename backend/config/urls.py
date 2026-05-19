"""Root URL configuration. URLs use /api/... (no v1 prefix)."""

from django.contrib import admin
from django.urls import path, include

from .health import health_check

urlpatterns = [
    # System
    path("admin/",  admin.site.urls),
    path("health/", health_check, name="health_check"),

    # Phase 0
    path("api/auth/",      include("apps.users.urls")),

    # Phase 1
    path("api/portfolio/", include("apps.portfolio.urls")),

    # Phase 2:
    path("api/journal/",   include("apps.journal.urls")),
    path("api/ai/",        include("apps.ai.urls")),

    # Phase 3+ adds:
    path("api/analytics/", include("apps.analytics.urls")),
]
