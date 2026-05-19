"""
AI views.

  POST /api/ai/analyze/                 — queue portfolio analysis
  POST /api/ai/journal/                 — queue journal entry generation
  POST /api/ai/chat/                    — synchronous portfolio chat
  GET  /api/ai/result/<task_id>/        — poll an async task result
  POST /api/ai/telegram/webhook/        — Telegram webhook receiver
  POST /api/ai/telegram/setup/          — register webhook with Telegram
"""

import json
import logging
import threading

from celery.result import AsyncResult
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .agents import route
from .tasks import handle_telegram_message, run_ai_agent
from .telegram import TelegramService, parse_telegram_command

logger = logging.getLogger(__name__)


# ─── Portfolio Analyst ────────────────────────────────────────────

class AnalyzePortfolioView(APIView):
    """
    POST /api/ai/analyze/

    No request body required — the agent fetches the user's live
    portfolio data via PortfolioService. Returns immediately with a
    task_id; poll /api/ai/result/<task_id>/ for completion.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        chat_id = request.user.telegram_chat_id or ""

        task = run_ai_agent.delay(
            "analyze",
            user_id=request.user.id,
            telegram_chat_id=chat_id,
        )
        return Response(
            {"task_id": task.id, "telegram_notify": bool(chat_id)},
            status=status.HTTP_202_ACCEPTED,
        )


# ─── Journal Writer ───────────────────────────────────────────────

class JournalWriterView(APIView):
    """
    POST /api/ai/journal/

    Body:
        { "trade_data": {
            "ticker": "PLTR", "asset_type": "call", "side": "buy",
            "quantity": 2, "price": 4.50,
            "strike": 160, "expiry": "2025-07-18"
          }
        }

    Queues a journal-writer task. The result is saved to Postgres as a
    JournalEntry (which auto-indexes to ES via post_save signal).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        trade_data = request.data.get("trade_data")
        if not trade_data:
            return Response(
                {"error": "trade_data is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chat_id = request.user.telegram_chat_id or ""

        task = run_ai_agent.delay(
            "journal",
            user_id=request.user.id,
            trade_data=trade_data,
            telegram_chat_id=chat_id,
        )
        return Response(
            {
                "task_id":          task.id,
                "telegram_notify":  bool(chat_id),
                "saves_to_journal": True,
            },
            status=status.HTTP_202_ACCEPTED,
        )


# ─── Portfolio Chat ───────────────────────────────────────────────

class PortfolioChatView(APIView):
    """
    POST /api/ai/chat/

    Body:
        { "question": "...", "history": [...] }

    Synchronous — returns the answer in the response. Used for fast
    one-off questions where polling adds latency we don't need.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = request.data.get("question")
        history  = request.data.get("history")
        chat_id  = request.user.telegram_chat_id or ""

        if not question:
            return Response(
                {"error": "question is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            answer = route(
                "chat",
                user_question=question,
                user_id=request.user.id,
                history=history or None,
            )
        except Exception as exc:
            logger.error("Chat agent failed: %s", exc)
            return Response(
                {"error": "Chat failed. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if chat_id:
            threading.Thread(
                target=TelegramService().send_message,
                kwargs={"chat_id": chat_id, "text": f"🤖 *Portfolio Assistant*\n\n{answer}"},
                daemon=True,
            ).start()

        return Response({"answer": answer})


# ─── Async result polling ─────────────────────────────────────────

class AIResultView(APIView):
    """
    GET /api/ai/result/<task_id>/

    Poll for the result of an async AI task queued by /analyze or
    /journal. States:
        pending  — task hasn't started yet
        started  — task is running
        success  — task completed, see "data"
        failure  — task raised an exception, see "error"
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id):
        result = AsyncResult(task_id)

        if result.state == "PENDING":
            return Response({"status": "pending"})
        if result.state == "STARTED":
            return Response({"status": "started"})
        if result.state == "SUCCESS":
            data = result.result or {}
            if data.get("user_id") and data["user_id"] != request.user.id:
                return Response({"status": "not_found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"status": "success", "data": data})
        if result.state == "FAILURE":
            return Response({"status": "failure", "error": str(result.result)})
        # RETRY, REVOKED, etc.
        return Response({"status": result.state.lower()})


# ─── Telegram webhook (unauthenticated, called by Telegram) ───────

@csrf_exempt
def telegram_webhook(request):
    """
    POST /api/ai/telegram/webhook/

    Receives Telegram updates and queues them for processing. Returns
    200 OK quickly so Telegram doesn't retry — actual work happens in
    the Celery task `handle_telegram_message`.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST only"}, status=405)

    secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != secret:
            logger.warning("Telegram webhook: invalid secret token from %s", request.META.get("REMOTE_ADDR"))
            return JsonResponse({"ok": True})

    try:
        body    = json.loads(request.body or b"{}")
        message = body.get("message") or body.get("edited_message") or {}

        if not message:
            # Pings, channel posts, callback queries — ignore
            return JsonResponse({"ok": True})

        chat_id  = str(message.get("chat", {}).get("id", ""))
        command, argument = parse_telegram_command(message)

        if not chat_id:
            return JsonResponse({"ok": True})

        handle_telegram_message.delay(
            chat_id=chat_id,
            command=command,
            argument=argument,
        )
    except Exception as exc:
        # Always return 200 — Telegram retries aggressively on errors.
        logger.error("Telegram webhook error: %s", exc)

    return JsonResponse({"ok": True})


class TelegramSetupView(APIView):
    """
    POST /api/ai/telegram/setup/

    Body: { "webhook_url": "https://your-domain.com" }

    Registers your public URL as Telegram's webhook for this bot.
    The actual webhook path /api/ai/telegram/webhook/ is appended
    automatically.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        base = request.data.get("webhook_url")
        if not base:
            return Response(
                {"error": "webhook_url is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        full_url = f"{base.rstrip('/')}/api/ai/telegram/webhook/"
        secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
        success = TelegramService().set_webhook(full_url, secret_token=secret)

        if success:
            return Response({"status": "webhook registered", "url": full_url})
        return Response(
            {"error": "Failed to register webhook"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
