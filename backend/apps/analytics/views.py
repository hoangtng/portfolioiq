"""
Analytics views — Phase 3 (fixed).

  GET  /api/analytics/history/      P&L history curve
  GET  /api/analytics/stats/        Win rate, profit factor, best/worst day
  GET  /api/analytics/performers/   Best (winners) and worst (losers)
  GET  /api/analytics/allocation/   Asset allocation by type & ticker
  GET  /api/analytics/realized/     Realized P&L by ticker and month
  POST /api/analytics/snapshot/     Manually trigger today's snapshot

Bug fixes vs. original:
  - int() parsing wrapped in try/except so ?days=abc returns 400, not 500
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    AssetAllocationSerializer,
    PerformanceStatsSerializer,
    PnLHistoryResponseSerializer,
    PortfolioSnapshotSerializer,
    RealizedSummarySerializer,
    TopPerformersSerializer,
)
from .services import AnalyticsService


def _parse_int_param(request, name: str, default: int, *, lo: int, hi: int):
    """
    Pull an int query parameter safely. Returns (value, error_response).

    On success: (parsed_int, None)
    On failure: (None, DRF Response with 400)

    Clamps to [lo, hi] on success.
    """
    raw = request.query_params.get(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, Response(
            {"detail": f"Query param '{name}' must be an integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return max(lo, min(value, hi)), None


class PnLHistoryView(APIView):
    """GET /api/analytics/history/?days=90"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        days, error = _parse_int_param(request, "days", 90, lo=1, hi=365)
        if error:
            return error

        data = AnalyticsService(request.user).get_pnl_history(days=days)
        serializer = PnLHistoryResponseSerializer({
            "days":    days,
            "count":   len(data),
            "history": data,
        })
        return Response(serializer.data)


class PerformanceStatsView(APIView):
    """GET /api/analytics/stats/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        stats = AnalyticsService(request.user).get_performance_stats()
        return Response(PerformanceStatsSerializer(stats).data)


class TopPerformersView(APIView):
    """GET /api/analytics/performers/?limit=5"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        limit, error = _parse_int_param(request, "limit", 5, lo=1, hi=20)
        if error:
            return error

        data = AnalyticsService(request.user).get_top_performers(limit=limit)
        return Response(TopPerformersSerializer(data).data)


class AssetAllocationView(APIView):
    """GET /api/analytics/allocation/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = AnalyticsService(request.user).get_asset_allocation()
        return Response(AssetAllocationSerializer(data).data)


class RealizedSummaryView(APIView):
    """GET /api/analytics/realized/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = AnalyticsService(request.user).get_realized_summary()
        return Response(RealizedSummarySerializer(data).data)


class TakeSnapshotView(APIView):
    """POST /api/analytics/snapshot/ — manual trigger (Celery does it daily)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        snapshot, created = AnalyticsService(request.user).take_snapshot()

        if snapshot is None:
            return Response(
                {"message": "No open positions — snapshot not taken."}, 
                status=status.HTTP_200_OK,
            )

        return Response(
            PortfolioSnapshotSerializer(snapshot).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
