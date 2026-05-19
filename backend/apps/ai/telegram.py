"""
Telegram service for outbound messages and webhook command parsing.

Used by:
  - apps.ai.tasks.run_ai_agent           (posts AI output back to chat)
  - apps.ai.tasks.handle_telegram_message (responds to inbound commands)
  - apps.ai.views.TelegramSetupView      (registers the webhook with Telegram)

Bot setup:
  1. Talk to @BotFather on Telegram, /newbot
  2. Save the token in TELEGRAM_BOT_TOKEN env var
  3. POST /api/ai/telegram/setup/ with your public webhook URL
"""

import logging
import re

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# Telegram caps a single message at 4096 chars. Stay under to leave
# headroom for our formatting headers (emoji + "*Title*\n\n").
TELEGRAM_MAX_LEN = 4000


class TelegramService:
    """Thin HTTP wrapper. All methods are best-effort — never raise."""

    def __init__(self, token: str | None = None, timeout: float = 10.0):
        self.token   = token or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.timeout = timeout
        self.base    = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    # ─── Outbound ─────────────────────────────────────────────

    def send_message(
        self,
        chat_id:    str | int,
        text:       str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """
        Send `text` to `chat_id`. Long messages are split into chunks.
        Returns True on full success, False on any chunk failure.
        Markdown errors fall back to plain text automatically.
        """
        if not self.base:
            logger.warning("Telegram disabled — no TELEGRAM_BOT_TOKEN set")
            return False
        if not text:
            return False

        chunks  = _chunk_text(text, TELEGRAM_MAX_LEN)
        all_ok  = True

        for chunk in chunks:
            ok = self._post_message(chat_id, chunk, parse_mode)
            if not ok and parse_mode:
                # Markdown can fail on legitimate text (e.g. an unescaped
                # underscore in a ticker). Retry without parse_mode.
                ok = self._post_message(chat_id, chunk, parse_mode=None)
            all_ok = all_ok and ok

        return all_ok

    def send_typing(self, chat_id: str | int) -> None:
        """Show 'typing...' indicator. Fire-and-forget."""
        if not self.base:
            return
        try:
            httpx.post(
                f"{self.base}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
                timeout=self.timeout,
            )
        except Exception as exc:
            logger.warning("Telegram sendChatAction failed: %s", exc)

    def set_webhook(self, url: str, secret_token: str = "") -> bool:
        """Register a webhook URL with Telegram. Returns success."""
        if not self.base:
            logger.error("Cannot set webhook — TELEGRAM_BOT_TOKEN missing")
            return False
        payload: dict = {"url": url, "allowed_updates": ["message"]}
        if secret_token:
            payload["secret_token"] = secret_token
        try:
            resp = httpx.post(
                f"{self.base}/setWebhook",
                json=payload,
                timeout=self.timeout,
            )
            data = resp.json()
            if data.get("ok"):
                logger.info("Telegram webhook set to %s", url)
                return True
            logger.error("Telegram setWebhook returned: %s", data)
            return False
        except Exception as exc:
            logger.error("Telegram setWebhook failed: %s", exc)
            return False

    # ─── Internal ─────────────────────────────────────────────

    def _post_message(self, chat_id, text, parse_mode):
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            resp = httpx.post(
                f"{self.base}/sendMessage", json=payload, timeout=self.timeout,
            )
            if resp.status_code == 200:
                return True
            logger.warning(
                "Telegram sendMessage %s: %s", resp.status_code, resp.text[:200],
            )
            return False
        except Exception as exc:
            logger.warning("Telegram sendMessage failed: %s", exc)
            return False


# ─── Helpers ──────────────────────────────────────────────────────

def _chunk_text(text: str, limit: int) -> list[str]:
    """Split `text` into ≤limit chunks, preferring paragraph and line breaks."""
    if len(text) <= limit:
        return [text]

    chunks    = []
    remaining = text
    while len(remaining) > limit:
        # Look for a natural break point in the last 20% of the window
        window = remaining[:limit]
        cut    = window.rfind("\n\n")
        if cut < limit * 0.7:
            cut = window.rfind("\n")
        if cut < limit * 0.5:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


_COMMAND_RE = re.compile(r"^/(\w+)(?:@\w+)?(?:\s+(.+))?$", re.DOTALL)


def parse_telegram_command(message: dict) -> tuple[str, str]:
    """
    Extract `(command, argument)` from a Telegram message dict.

    "/analyze"             -> ("analyze", "")
    "/chat what's my risk" -> ("chat", "what's my risk")
    "/journal@MyBot hello" -> ("journal", "hello")
    "hi there"             -> ("", "hi there")    (no leading slash)
    """
    text = (message.get("text") or "").strip()
    if not text:
        return ("", "")

    m = _COMMAND_RE.match(text)
    if not m:
        return ("", text)

    return (m.group(1).lower(), (m.group(2) or "").strip())
