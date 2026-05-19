"""
AI agents — Phase 2.

Three agents, one dispatcher:

  run_portfolio_analyst(user_id)
    Fetches live portfolio data and asks Claude to analyze it. No manual
    input required — pulls Postgres + Redis state via PortfolioService.

  run_journal_writer(trade_data, user_id=None)
    Generates a journal entry for a specific trade. If user_id is given,
    enriches the prompt with current portfolio context.

  run_portfolio_chat(user_question, user_id=None, portfolio_data=None, history=None)
    Free-form Q&A. Either pulls live portfolio (preferred) or accepts
    portfolio_data directly. Optional conversation history list.

  route(agent_name, **kwargs)
    Dispatcher. Used by Celery tasks and the chat view.
"""

import anthropic
from django.conf import settings

from .prompts import (
    JOURNAL_WRITER_PROMPT,
    PORTFOLIO_ANALYST_PROMPT,
    PORTFOLIO_CHAT_PROMPT,
)

MODEL = "claude-sonnet-4-6"

_client: anthropic.Anthropic | None = None

    
def get_client() -> anthropic.Anthropic:
    """Lazy singleton — avoids constructing the client at import time."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _call_claude(system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
    """Single source of truth for Claude calls — easy to mock in tests."""
    message = get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


# ─── Portfolio context builder ────────────────────────────────────

def _build_portfolio_context(user) -> dict:
    """
    Build a JSON-friendly snapshot of the user's portfolio.

    Pulls open positions from Postgres and current prices from Redis
    (via PortfolioService). Decimals are converted to floats so the
    result can be JSON-serialized and embedded in a Claude prompt.
    """
    from apps.portfolio.services.portfolio import PortfolioService
    from apps.portfolio.services.cache import QuoteCache

    summary = PortfolioService(user).get_summary()
    cache   = QuoteCache()

    positions_data = []
    for position in summary["positions"]:
        quote = cache.get(position.ticker)
        current_price = float(quote["price"]) if quote else None

        p = {
            "ticker":             position.ticker,
            "asset_type":         position.asset_type,
            "quantity":           float(position.quantity),
            "avg_cost":           float(position.avg_cost),
            "current_price":      current_price,
            "unrealized_pnl":     float(position.unrealized_pnl(current_price))     if current_price else None,
            "unrealized_pnl_pct": float(position.unrealized_pnl_pct(current_price)) if current_price else None,
        }
        if position.strike:
            p["strike"] = float(position.strike)
            p["expiry"] = str(position.expiry)
        positions_data.append(p)

    return {
        "total_cost_basis":         float(summary["total_cost_basis"]),
        "total_market_value":       float(summary["total_market_value"]),
        "total_unrealized_pnl":     float(summary["total_unrealized_pnl"]),
        "total_unrealized_pnl_pct": float(summary["total_unrealized_pnl_pct"]),
        "positions_count":          summary["positions_count"],
        "prices_cached":            summary["prices_cached"],
        "positions":                positions_data,
    }


def _format_positions(positions: list[dict]) -> str:
    """Render positions as a human-readable text block for prompts."""
    if not positions:
        return "  (no open positions)"

    lines = []
    for p in positions:
        line = f"  - {p['ticker']} {p.get('asset_type', 'stock').upper()}"
        line += f" | qty: {p['quantity']} | avg: ${p.get('avg_cost', 0):.2f}"
        if p.get("current_price"):
            line += f" | now: ${p['current_price']:.2f}"
        if p.get("unrealized_pnl") is not None:
            line += f" | P&L: ${p['unrealized_pnl']:.2f}"
        if p.get("strike"):
            line += f" | strike ${p['strike']} exp {p.get('expiry')}"
        lines.append(line)
    return "\n".join(lines)


# ─── Agent 1: Portfolio Analyst ───────────────────────────────────

def run_portfolio_analyst(user_id: int) -> str:
    """Pull live portfolio data and ask Claude to analyze it."""
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.get(id=user_id)
    portfolio_data = _build_portfolio_context(user)

    if portfolio_data["positions_count"] == 0:
        return (
            "Your portfolio is empty. Add some positions first, "
            "then come back for an analysis."
        )

    user_message = f"""\
Please analyze my portfolio:

Total cost basis:    ${portfolio_data['total_cost_basis']:,.2f}
Total market value:  ${portfolio_data['total_market_value']:,.2f}
Total unrealized P&L: ${portfolio_data['total_unrealized_pnl']:,.2f} ({portfolio_data['total_unrealized_pnl_pct']:.1f}%)
Prices cached: {portfolio_data['prices_cached']}

Positions:
{_format_positions(portfolio_data['positions'])}
"""
    return _call_claude(PORTFOLIO_ANALYST_PROMPT, user_message, max_tokens=700)


# ─── Agent 2: Journal Writer ──────────────────────────────────────

def run_journal_writer(trade_data: dict, user_id: int | None = None) -> str:
    """
    Generate a journal entry for one trade. Optional user_id enriches
    the prompt with portfolio context.
    """
    portfolio_context_str = ""

    if user_id:
        try:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.get(id=user_id)
            ctx  = _build_portfolio_context(user)
            portfolio_context_str = (
                "\nCurrent portfolio context:\n"
                + _format_positions(ctx["positions"])
            )
        except Exception:
            # Portfolio enrichment is best-effort. Continue without it
            # if anything goes wrong (user deleted, ES down, etc.).
            pass

    # Build the trade summary block. Each field is optional so the prompt
    # stays clean when the user only provided a few details.
    lines = []
    lines.append(f"Ticker:   {trade_data.get('ticker', 'UNKNOWN')}")
    lines.append(f"Type:     {trade_data.get('asset_type', 'stock')}")
    lines.append(f"Side:     {trade_data.get('side', 'buy').upper()}")
    lines.append(f"Quantity: {trade_data.get('quantity', 0)}")

    price = trade_data.get("price")
    if price is not None:
        lines.append(f"Price:    ${float(price):.2f}")
    if trade_data.get("strike"):
        lines.append(f"Strike:   ${trade_data['strike']}")
    if trade_data.get("expiry"):
        lines.append(f"Expiry:   {trade_data['expiry']}")
    if trade_data.get("raw_note"):
        lines.append(f"Notes:    {trade_data['raw_note']}")

    user_message = (
        "Write a journal entry for this trade:\n\n"
        + "\n".join(lines)
        + portfolio_context_str
    )
    return _call_claude(JOURNAL_WRITER_PROMPT, user_message, max_tokens=500)


# ─── Agent 3: Portfolio Chat ──────────────────────────────────────

def run_portfolio_chat(
    user_question:  str,
    user_id:        int | None = None,
    portfolio_data: dict | None = None,
    history:        list | None = None,
) -> str:
    """
    Free-form Q&A with portfolio context.

    user_id is preferred — fetches live data. If portfolio_data is given
    instead (e.g. in tests), uses that. history is an optional list of
    prior messages in Claude format: [{"role": "user"|"assistant", "content": "..."}]
    """
    if user_id and not portfolio_data:
        try:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.get(id=user_id)
            portfolio_data = _build_portfolio_context(user)
        except Exception:
            portfolio_data = {}

    portfolio_data = portfolio_data or {}

    portfolio_context = (
        f"Current portfolio:\n"
        f"Total value: ${portfolio_data.get('total_market_value', 0):,.2f}\n"
        f"Total P&L:   ${portfolio_data.get('total_unrealized_pnl', 0):,.2f}\n\n"
        f"Positions:\n{_format_positions(portfolio_data.get('positions', []))}\n---\n\n"
    )

    if history:
        messages = list(history)
        # Inject portfolio context into the latest user message without mutating caller's dict
        messages[-1] = {**messages[-1], "content": portfolio_context + messages[-1]["content"]}
    else:
        messages = [{"role": "user", "content": portfolio_context + user_question}]

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=512,
        system=PORTFOLIO_CHAT_PROMPT,
        messages=messages,
    )
    return response.content[0].text


# ─── Dispatcher ───────────────────────────────────────────────────

AGENT_MAP = {
    "analyze": run_portfolio_analyst,
    "journal": run_journal_writer,
    "chat":    run_portfolio_chat,
}


def route(agent_name: str, **kwargs) -> str:
    """Dispatch to the named agent. Raises ValueError for unknown names."""
    if agent_name not in AGENT_MAP:
        raise ValueError(
            f"Unknown agent: {agent_name!r}. Valid: {list(AGENT_MAP)}"
        )
    return AGENT_MAP[agent_name](**kwargs)
