"""
Portfolio routes mounted at /api/portfolio/

  GET            summary/
  GET POST       watchlist/
  GET DELETE     watchlist/{id}/
  GET POST       positions/
  GET PATCH DEL  positions/{id}/
  GET POST       positions/{id}/trades/
  GET POST       alerts/
  GET DELETE     alerts/{id}/
  GET            quote/{ticker}/
  GET            options/{ticker}/
"""

from django.urls import path

from .views import (
    OptionsChainView,
    PortfolioSummaryView,
    PositionDetailView,
    PositionListCreateView,
    PriceAlertDetailView,
    PriceAlertListCreateView,
    QuoteView,
    TradeListCreateView,
    WatchlistDetailView,
    WatchlistListCreateView,
)

urlpatterns = [
    path("summary/",                            PortfolioSummaryView.as_view(),     name="portfolio_summary"),
    path("watchlist/",                          WatchlistListCreateView.as_view(),  name="watchlist_list"),
    path("watchlist/<int:pk>/",                 WatchlistDetailView.as_view(),      name="watchlist_detail"),
    path("positions/",                          PositionListCreateView.as_view(),   name="position_list"),
    path("positions/<int:pk>/",                 PositionDetailView.as_view(),       name="position_detail"),
    path("positions/<int:position_id>/trades/", TradeListCreateView.as_view(),      name="trade_list"),
    path("alerts/",                             PriceAlertListCreateView.as_view(), name="alert_list"),
    path("alerts/<int:pk>/",                    PriceAlertDetailView.as_view(),     name="alert_detail"),
    path("quote/<str:ticker>/",                 QuoteView.as_view(),                name="quote"),
    path("options/<str:ticker>/",               OptionsChainView.as_view(),         name="options_chain"),
]
