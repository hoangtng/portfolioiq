from django.urls import path

from .views import (
    AssetAllocationView,
    PerformanceStatsView,
    PnLHistoryView,
    RealizedSummaryView,
    TakeSnapshotView,
    TopPerformersView,
)

urlpatterns = [
    path("history/",    PnLHistoryView.as_view(),        name="analytics_history"),
    path("stats/",      PerformanceStatsView.as_view(),  name="analytics_stats"),
    path("performers/", TopPerformersView.as_view(),     name="analytics_performers"),
    path("allocation/", AssetAllocationView.as_view(),   name="analytics_allocation"),
    path("realized/",   RealizedSummaryView.as_view(),   name="analytics_realized"),
    path("snapshot/",   TakeSnapshotView.as_view(),      name="analytics_snapshot"),
]
