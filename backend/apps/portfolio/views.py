"""
Portfolio views — 10 API endpoints. Views are thin; business logic is in services/.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal

from django.core.cache import cache
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PriceAlert, Position, Trade, Watchlist
from .serializers import (
    PortfolioSummarySerializer,
    PositionCreateSerializer,
    PositionSerializer,
    PriceAlertSerializer,
    TradeSerializer,
    WatchlistSerializer,
)
from .services.cache import QuoteCache
from .services.market import MassiveClient
from .services.portfolio import PortfolioService

logger = logging.getLogger(__name__)


# ─── Portfolio summary ────────────────────────────────────────

class PortfolioSummaryView(APIView):
    """GET /api/portfolio/summary/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        summary    = PortfolioService(request.user).get_summary()
        serializer = PortfolioSummarySerializer(summary)
        return Response(serializer.data)


# ─── Watchlist ────────────────────────────────────────────────

class WatchlistListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/portfolio/watchlist/"""
    serializer_class   = WatchlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WatchlistDetailView(generics.RetrieveDestroyAPIView):
    """GET / DELETE /api/portfolio/watchlist/{id}/"""
    serializer_class   = WatchlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)


# ─── Positions ────────────────────────────────────────────────

class PositionListCreateView(generics.ListCreateAPIView):
    """
    GET / POST /api/portfolio/positions/

    Query params: ?is_open=true|false (default true), ?ticker=PLTR
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PositionCreateSerializer
        return PositionSerializer

    def get_queryset(self):
        qs = Position.objects.filter(user=self.request.user).prefetch_related("trades")
        is_open = self.request.query_params.get("is_open", "true").lower()
        qs = qs.filter(is_open=(is_open != "false"))
        ticker = self.request.query_params.get("ticker")
        if ticker:
            qs = qs.filter(ticker=ticker.upper())
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PositionDetailView(generics.RetrieveDestroyAPIView):
    """GET / DELETE /api/portfolio/positions/{id}/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = PositionSerializer

    def get_queryset(self):
        return Position.objects.filter(user=self.request.user).prefetch_related("trades")


# ─── Trades ───────────────────────────────────────────────────

class TradeListCreateView(generics.ListCreateAPIView):
    """
    GET / POST /api/portfolio/positions/{position_id}/trades/

    POST automatically:
      - Updates avg_cost on buys
      - Calculates realized_pnl on sells
      - Closes the position when sell quantity reaches 0
    """
    serializer_class   = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_position(self) -> Position:
        if not hasattr(self, "_position"):
            self._position = Position.objects.get(
                id=self.kwargs["position_id"],
                user=self.request.user,
            )
        return self._position

    def get_queryset(self):
        return Trade.objects.filter(position=self._get_position())

    def perform_create(self, serializer):
        position = self._get_position()

        if not position.is_open:
            raise ValidationError("Cannot add a trade to a closed position.")

        executed_at = None
        raw = self.request.data.get("executed_at")
        if raw:
            try:
                executed_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        try:
            trade = PortfolioService(self.request.user).record_trade(
                position    = position,
                side        = serializer.validated_data["side"],
                quantity    = serializer.validated_data["quantity"],
                price       = serializer.validated_data["price"],
                fees        = serializer.validated_data.get("fees", Decimal("0")),
                executed_at = executed_at,
                notes       = serializer.validated_data.get("notes", ""),
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        serializer.instance = trade


# ─── Price alerts ─────────────────────────────────────────────

class PriceAlertListCreateView(generics.ListCreateAPIView):
    """
    GET / POST /api/portfolio/alerts/
    Query param: ?active=true (active alerts only)
    """
    serializer_class   = PriceAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = PriceAlert.objects.filter(user=self.request.user)
        if self.request.query_params.get("active") == "true":
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PriceAlertDetailView(generics.RetrieveDestroyAPIView):
    """GET / DELETE /api/portfolio/alerts/{id}/"""
    serializer_class   = PriceAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user)


# ─── Single-ticker quote ──────────────────────────────────────

class QuoteView(APIView):
    """
    GET /api/portfolio/quote/{ticker}/

    Returns cached quote. On cache miss, tries snapshot (paid),
    falls back to previous-close (free tier).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, ticker):
        ticker = ticker.upper()
        qcache = QuoteCache()
        quote  = qcache.get(ticker)

        if not quote:
            client = MassiveClient()
            try:
                quotes = client.get_snapshot([ticker])
                quote  = quotes.get(ticker)
            except Exception as exc:
                logger.warning("Snapshot fetch failed for %s: %s", ticker, exc)
                quote = None

            if not quote:
                quote = client.get_previous_close(ticker)

            if quote:
                qcache.set(ticker, quote)

        if not quote:
            return Response(
                {"error": f"No price data available for {ticker}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"ticker": ticker, **quote})


# ─── Options chain ────────────────────────────────────────────

class OptionsChainView(APIView):
    """
    GET /api/portfolio/options/{ticker}/

    Cached for 5 min. Requires Options Starter+ plan.
    Query params: ?expiry, ?type=call|put, ?strike_gte, ?strike_lte, ?limit
    """
    permission_classes = [permissions.IsAuthenticated]
    CACHE_TTL = 300

    def get(self, request, ticker):
        ticker     = ticker.upper()
        expiry     = request.query_params.get("expiry")
        ctype      = request.query_params.get("type")
        strike_gte = request.query_params.get("strike_gte")
        strike_lte = request.query_params.get("strike_lte")
        try:
            limit = min(int(request.query_params.get("limit", 100)), 250)
        except ValueError:
            limit = 100

        cache_key = (
            f"options:{ticker}:{expiry or 'all'}:{ctype or 'all'}"
            f":{strike_gte or ''}:{strike_lte or ''}:{limit}"
        )

        cached = cache.get(cache_key)
        if cached:
            contracts = json.loads(cached)
            return Response({
                "ticker":     ticker,
                "contracts":  contracts,
                "from_cache": True,
                "count":      len(contracts),
            })

        contracts = MassiveClient().get_options_chain(
            ticker        = ticker,
            expiry        = expiry,
            contract_type = ctype,
            strike_gte    = float(strike_gte) if strike_gte else None,
            strike_lte    = float(strike_lte) if strike_lte else None,
            limit         = limit,
        )

        cache.set(cache_key, json.dumps(contracts), timeout=self.CACHE_TTL)

        return Response({
            "ticker":     ticker,
            "contracts":  contracts,
            "from_cache": False,
            "count":      len(contracts),
        })
