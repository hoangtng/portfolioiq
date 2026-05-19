from django.urls import path

from .views import (
    AIResultView,
    AnalyzePortfolioView,
    JournalWriterView,
    PortfolioChatView,
    TelegramSetupView,
    telegram_webhook,
)

urlpatterns = [
    path("analyze/",                AnalyzePortfolioView.as_view(), name="ai_analyze"),
    path("journal/",                JournalWriterView.as_view(),    name="ai_journal"),
    path("chat/",                   PortfolioChatView.as_view(),    name="ai_chat"),
    path("result/<str:task_id>/",   AIResultView.as_view(),         name="ai_result"),
    path("telegram/webhook/",       telegram_webhook,               name="telegram_webhook"),
    path("telegram/setup/",         TelegramSetupView.as_view(),    name="telegram_setup"),
]
