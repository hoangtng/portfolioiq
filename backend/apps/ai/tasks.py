"""
Celery tasks for AI work.

Why async? Claude responses take 5-30 seconds. We don't want the HTTP
request to hang that long. The view returns a task_id immediately;
the client polls /ai/result/{task_id}/ until done.

Telegram message handling is also a Celery task so the webhook can
return 200 immediately without waiting for Claude.
"""

import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from .agents import route
from .telegram import TelegramService

logger = logging.getLogger(__name__)
User   = get_user_model()


@shared_task(bind=True, name="ai.run_agent")
def run_ai_agent(self, agent_name: str, user_id: int, **kwargs) -> dict:
    """
    Run a Claude agent and return its text response.

    For "journal" agent, also persists the result as a JournalEntry.

    Args:
        agent_name: one of "analyze", "journal", "chat"
        user_id:    DB id of the requesting user
        **kwargs:   passed to the agent function. For "journal",
                    should include trade_data={...}

    Returns: { "status": "ok", "response": "...", "saved_entry_id"?: int }
             { "status": "error", "error": "..." }
    """
    telegram_chat_id = kwargs.pop("telegram_chat_id", None)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "error", "error": f"User {user_id} not found"}

    try:
        response = route(agent_name, user_id=user.id, **kwargs)
    except ValueError as exc:
        logger.error("Agent %s failed: %s", agent_name, exc)
        return {"status": "error", "error": str(exc)}

    result = {"status": "ok", "response": response, "user_id": user_id}

    if agent_name == "journal" and kwargs.get("trade_data"):
        entry = _save_journal_entry(user, response, kwargs["trade_data"])
        if entry:
            result["saved_entry_id"] = entry.id

    if telegram_chat_id:
        TelegramService().send_message(chat_id=telegram_chat_id, text=response)

    return result


def _save_journal_entry(user, result: str, trade_data: dict):
    """
    Parse the agent's markdown output and save it as a JournalEntry.

    Expected format:
        # Title goes here

        Body paragraph 1...
    """
    from apps.journal.models import JournalEntry

    if user is None:
        logger.error("_save_journal_entry: user is required")
        return None

    if not isinstance(trade_data, dict):
        logger.error("_save_journal_entry: trade_data must be a dict, got %s", type(trade_data))
        trade_data = {}

    ticker = (trade_data.get("ticker") or "").strip()
    side   = (trade_data.get("side") or "buy").strip()
    asset  = (trade_data.get("asset_type") or "stock").strip()

    # Extract title from the AI output
    lines = [ln.strip() for ln in result.split("\n") if ln.strip()]
    title_line = lines[0] if lines else f"{side.upper()} {ticker} — AI Journal"

    title = title_line.lstrip("# ").strip()
    title = title.replace("**", "").replace("*", "").strip()

    if len(title) > 200:
        title = title[:197] + "..."
    if not title:
        title = f"{side.upper()} {ticker} — AI Journal" if ticker else "AI Journal Entry"

    # Build tags — drop empties so we don't store ""
    tags = [t for t in [
        ticker.lower() if ticker else None,
        side.lower(),
        asset.lower(),
        "ai-generated",
    ] if t]

    return JournalEntry.objects.create(
        user=user,
        title=title,
        body=result,
        ticker=ticker.upper() if ticker else "",
        tags=tags,
        ai_generated=True,
        trade_id=trade_data.get("trade_id"),
    )


@shared_task(name="ai.handle_telegram_message")
def handle_telegram_message(chat_id: str, command: str, argument: str) -> dict:
    """
    Process a parsed Telegram command (called from the webhook view).

    The webhook view returns 200 immediately and passes the already-parsed
    command so this task doesn't need to re-parse the raw update.

    Supported commands:
        /start            link your account
        /analyze          run portfolio analyst
        /chat <question>  free-form portfolio Q&A
        /journal <ticker> <thesis>   generate journal entry
        /help             show usage
    """
    telegram = TelegramService()

    # Find the user by chat_id (set via /api/auth/me/ PATCH)
    user = User.objects.filter(telegram_chat_id=str(chat_id)).first()

    # ─── /start — onboarding ─────────────────────────────────
    if command == "start":
        if user:
            telegram.send_message(
                chat_id=chat_id,
                text=f"You're all set, {user.display_name} 👋\n\nReady when you are — try /analyze for a portfolio check, or /help to see what I can do.",
            )
        else:
            telegram.send_message(
                chat_id=chat_id,
                text=(
                    f"Hey there 👋\n\n"
                    f"I'm PortfolioIQ — an AI analyst that actually knows your portfolio. "
                    f"Before we get started, I need to link this Telegram to your account.\n\n"
                    f"Here's your chat ID: `{chat_id}`\n\n"
                    f"Pop over to https://portfolioiq.online/settings, paste it into the "
                    f"Telegram field, and hit save. Takes about 10 seconds.\n\n"
                    f"Once you're linked, try:\n\n"
                    f"📊 /analyze — Full portfolio breakdown\n"
                    f"💬 /chat — Ask me anything about your book\n"
                    f"📋 /positions — Quick snapshot of what you hold\n"
                    f"❓ /help — See everything I can do\n\n"
                    f"See you in a sec."
                ),
            )
        return {"status": "ok", "command": "start"}

    # ─── All other commands require a linked account ─────────
    if not user:
        telegram.send_message(
            chat_id=chat_id,
            text="Hey there 👋 This Telegram account isn't linked to a PortfolioIQ profile yet.\n\nSend /start and I'll walk you through it — takes about 10 seconds.",
        )
        return {"status": "unlinked"}

    # ─── /help ────────────────────────────────────────────────
    if command == "help":
        telegram.send_message(
            chat_id=chat_id,
            text=(
                "*What I can do* 📊\n\n"
                "📈 /analyze — Full portfolio analysis\n"
                "💬 /chat — Ask anything about your book\n"
                "📝 /journal — Generate journal entries\n"
                "❓ /help — Show this menu\n\n"
                "_Tip: /chat What's risky right now?_\n\n"
                "🌐 portfolioiq.online"
            ),
        )
        return {"status": "ok", "command": "help"}

    # ─── /analyze ─────────────────────────────────────────────
    if command == "analyze":
        telegram.send_typing(chat_id)
        try:
            response = route("analyze", user_id=user.id)
        except ValueError as exc:
            telegram.send_message(chat_id=chat_id, text=f"Sorry, that failed: {exc}")
            return {"status": "error", "error": str(exc)}

        telegram.send_message(chat_id=chat_id, text=response)
        return {"status": "ok", "command": "analyze"}

    # ─── /chat <question> ─────────────────────────────────────
    if command == "chat":
        if not argument:
            telegram.send_message(
                chat_id=chat_id,
                text="Usage: `/chat <your question>`",
            )
            return {"status": "missing_args"}

        telegram.send_typing(chat_id)
        try:
            response = route("chat", user_id=user.id, user_question=argument)
        except ValueError as exc:
            telegram.send_message(chat_id=chat_id, text=f"Sorry, that failed: {exc}")
            return {"status": "error", "error": str(exc)}

        telegram.send_message(chat_id=chat_id, text=response)
        return {"status": "ok", "command": "chat"}

    # ─── /journal <ticker> <thesis> ───────────────────────────
    if command == "journal":
        parts = argument.split(maxsplit=1)
        if len(parts) < 2:
            telegram.send_message(
                chat_id=chat_id,
                text="Usage: `/journal <ticker> <thesis>`\nExample: `/journal PLTR breakout above 25 with strong volume`",
            )
            return {"status": "missing_args"}

        ticker, thesis = parts[0], parts[1]
        trade_data = {"ticker": ticker, "raw_note": thesis}
        telegram.send_typing(chat_id)
        try:
            response = route("journal", user_id=user.id, trade_data=trade_data)
        except ValueError as exc:
            telegram.send_message(chat_id=chat_id, text=f"Sorry, that failed: {exc}")
            return {"status": "error", "error": str(exc)}

        entry = _save_journal_entry(user, response, trade_data)
        if entry:
            telegram.send_message(
                chat_id=chat_id,
                text=f"Journal entry saved (#{entry.id})\n\n{response[:1500]}",
            )
            return {"status": "ok", "command": "journal", "saved_entry_id": entry.id}
        telegram.send_message(chat_id=chat_id, text=response[:1500])
        return {"status": "ok", "command": "journal"}

    # ─── Unknown ──────────────────────────────────────────────
    telegram.send_message(
        chat_id=chat_id,
        text=f"Unknown command: /{command}. Send /help for a list.",
    )
    return {"status": "unknown_command", "command": command}
