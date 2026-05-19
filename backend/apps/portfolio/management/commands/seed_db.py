"""
Seed the database with realistic demo data.

Usage:
  docker compose exec api python manage.py seed_db
  docker compose exec api python manage.py seed_db --email user@example.com
  docker compose exec api python manage.py seed_db --reset

What gets created (all tied to one user):
  - 6 open positions: NVDA, AAPL, META, MSFT, TSLA (stocks) + NVDA 900C (call)
  - Trades for each position (backdated)
  - 6 price alerts (3 active, 3 triggered — 2 recent, 1 old)
  - 5 watchlist items
  - 5 journal entries
  - 90 days of PortfolioSnapshot rows (powers the P&L history chart)

Idempotent — skips records that already exist.
Use --reset to wipe the user's portfolio data first.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.portfolio.models import Position, PriceAlert, Trade, Watchlist
from apps.portfolio.models_snapshot import PortfolioSnapshot
from apps.portfolio.services.cache import QuoteCache
from apps.journal.models import JournalEntry

User = get_user_model()


def _dt(days_back: int):
    """Return a timezone-aware datetime N days in the past."""
    return timezone.now() - timedelta(days=days_back)


def _date(days_back: int) -> date:
    return date.today() - timedelta(days=days_back)


# ─── Seed data ────────────────────────────────────────────────

POSITIONS = [
    {
        "ticker": "NVDA", "asset_type": "stock",
        "quantity": "50", "avg_cost": "420.60",
        "opened_days_ago": 95,
        "trades": [
            {"side": "buy", "qty": "30", "price": "405.00", "days_ago": 95, "notes": "AI thesis"},
            {"side": "buy", "qty": "20", "price": "441.00", "days_ago": 60, "notes": "Earnings add"},
        ],
    },
    {
        "ticker": "AAPL", "asset_type": "stock",
        "quantity": "100", "avg_cost": "165.00",
        "opened_days_ago": 120,
        "trades": [
            {"side": "buy", "qty": "50", "price": "158.40", "days_ago": 120, "notes": "Initial position"},
            {"side": "buy", "qty": "50", "price": "171.60", "days_ago": 75,  "notes": "Add on dip"},
        ],
    },
    {
        "ticker": "META", "asset_type": "stock",
        "quantity": "15", "avg_cost": "480.67",
        "opened_days_ago": 70,
        "trades": [
            {"side": "buy", "qty": "10", "price": "475.00", "days_ago": 70, "notes": "Ad market recovery"},
            {"side": "buy", "qty": "5",  "price": "492.00", "days_ago": 45, "notes": "Scale in"},
        ],
    },
    {
        "ticker": "MSFT", "asset_type": "stock",
        "quantity": "30", "avg_cost": "378.50",
        "opened_days_ago": 85,
        "trades": [
            {"side": "buy", "qty": "30", "price": "378.50", "days_ago": 85, "notes": "Copilot cycle"},
        ],
    },
    {
        "ticker": "NVDA", "asset_type": "call",
        "quantity": "2", "avg_cost": "16.80",
        "strike": "900.00",
        "expiry_days_from_now": 30,
        "opened_days_ago": 35,
        "trades": [
            {"side": "buy", "qty": "2", "price": "16.80", "fees": "1.30",
             "days_ago": 35, "notes": "900C lottery ticket"},
        ],
    },
    {
        "ticker": "TSLA", "asset_type": "stock",
        "quantity": "20", "avg_cost": "201.30",
        "opened_days_ago": 50,
        "trades": [
            {"side": "buy", "qty": "20", "price": "201.30", "days_ago": 50, "notes": "Bounce play"},
        ],
    },
    # Closed positions — these populate win rate, profit factor, and avg win/loss
    {
        "ticker": "AMZN", "asset_type": "stock",
        "quantity": "0", "avg_cost": "172.00",
        "is_open": False,
        "opened_days_ago": 80,
        "closed_days_ago": 30,
        "trades": [
            {"side": "buy",  "qty": "20", "price": "172.00", "days_ago": 80, "notes": "AWS re-acceleration play"},
            {"side": "sell", "qty": "20", "price": "184.50", "days_ago": 30,
             "realized_pnl": "250.00", "notes": "Target hit — clean exit"},
        ],
    },
    {
        "ticker": "AMD", "asset_type": "stock",
        "quantity": "0", "avg_cost": "153.00",
        "is_open": False,
        "opened_days_ago": 55,
        "closed_days_ago": 22,
        "trades": [
            {"side": "buy",  "qty": "15", "price": "153.00", "days_ago": 55, "notes": "Data center thesis"},
            {"side": "sell", "qty": "15", "price": "144.00", "days_ago": 22,
             "realized_pnl": "-135.00", "notes": "Stop hit — thesis wrong near-term"},
        ],
    },
]

ALERTS = [
    # Active — watching
    {"ticker": "NVDA", "condition": "above", "target_price": "900.00",
     "is_active": True},
    {"ticker": "AAPL", "condition": "below", "target_price": "170.00",
     "is_active": True},
    {"ticker": "TSLA", "condition": "above", "target_price": "220.00",
     "is_active": True},
    # Triggered recently (< 24 h) — these fire the dashboard badge + banner
    {"ticker": "MSFT", "condition": "above", "target_price": "420.00",
     "is_active": False, "triggered_price": "421.88", "triggered_days_ago": 0},
    {"ticker": "META", "condition": "above", "target_price": "580.00",
     "is_active": False, "triggered_price": "583.20", "triggered_days_ago": 0},
    # Triggered 5 days ago — historical, badge already dismissed
    {"ticker": "META", "condition": "above", "target_price": "600.00",
     "is_active": False, "triggered_price": "601.30", "triggered_days_ago": 5},
]

WATCHLIST = [
    {"ticker": "AMZN",  "notes": "AWS re-acceleration thesis"},
    {"ticker": "GOOGL", "notes": "Search + Gemini moat"},
    {"ticker": "AMD",   "notes": "Datacenter GPU competition"},
    {"ticker": "PLTR",  "notes": "AIP enterprise growth"},
    {"ticker": "CRM",   "notes": "Agentforce cycle"},
]

JOURNAL = [
    {
        "title": "NVDA — AI Infrastructure Supercycle",
        "ticker": "NVDA", "tags": ["ai", "semiconductor", "swing"],
        "ai_generated": False, "days_ago": 90,
        "body": (
            "## Thesis\n\nNVIDIA remains the picks-and-shovels play for the AI build-out. "
            "H100/H200 allocations are sold out through 2024 and the Blackwell transition adds another leg.\n\n"
            "## Entry\nAveraged in at $420 across two tranches. Position represents ~22% of portfolio.\n\n"
            "## Risk\n- Multiple compression if AI capex slows\n"
            "- AMD MI300X gaining share in inference\n"
            "- Export controls a wildcard\n\n"
            "## Exit plan\nHold through Blackwell ramp. Re-evaluate at $1000 if narrative shifts."
        ),
    },
    {
        "title": "AAPL — Services Flywheel Deep Dive",
        "ticker": "AAPL", "tags": ["services", "mega-cap", "hold"],
        "ai_generated": True, "days_ago": 75,
        "body": (
            "## Summary\n\nApple Services revenue hit $24.2B last quarter, growing 14% YoY. "
            "The flywheel — devices → ecosystem → services — keeps compounding.\n\n"
            "## Key metrics\n- 2.2B active devices\n"
            "- App Store + subscriptions = high-margin recurring\n"
            "- Vision Pro TAM unknown but optionality is real\n\n"
            "## Position\n100 shares @ $165 avg. Classic 'sleep well at night' holding."
        ),
    },
    {
        "title": "TSLA — Bounce Setup Not Working",
        "ticker": "TSLA", "tags": ["ev", "mean-reversion", "mistake"],
        "ai_generated": False, "days_ago": 45,
        "body": (
            "## Current situation\n\nEntered TSLA at $201 expecting a bounce off the $200 support. "
            "That level broke and stock is now trading at $175.\n\n"
            "## Lessons\n- Don't fight a downtrend with a mean-reversion trade\n"
            "- Volume on the breakdown was heavy — institutional selling\n"
            "- Energy storage thesis is intact but near-term headwinds from EV price war\n\n"
            "## Action\nSmall position, will cut if $165 breaks. Not adding."
        ),
    },
    {
        "title": "META — Advertising Cycle Recovery",
        "ticker": "META", "tags": ["social", "advertising", "ai"],
        "ai_generated": False, "days_ago": 60,
        "body": (
            "## Thesis\n\nMeta's ad platform is the strongest in social after the ATT recovery. "
            "Llama + AI ad optimization driving CPM improvements.\n\n"
            "## Numbers\n- Revenue growth re-accelerating to 27% YoY\n"
            "- Reels monetization approaching Stories parity\n"
            "- Reality Labs losses stabilizing\n\n"
            "## Trade\n15 shares averaged at $481. Medium conviction, smaller size than NVDA."
        ),
    },
    {
        "title": "Portfolio Review — Q1 2025",
        "ticker": "", "tags": ["review", "quarterly"],
        "ai_generated": False, "days_ago": 25,
        "body": (
            "## Performance\n\nPortfolio up ~$33K unrealized since January. "
            "NVDA carrying most of the return.\n\n"
            "## What worked\n- Concentrated position in AI infrastructure (NVDA)\n"
            "- Quick cut on losing trade (closed AMD puts)\n\n"
            "## What didn't\n- TSLA bounce trade — wrong market context\n"
            "- Missed AMZN breakout, was on watchlist for 2 weeks\n\n"
            "## Goals for Q2\n- Trim NVDA if it hits $1000 (position sizing discipline)\n"
            "- Build AMZN position on next pullback\n"
            "- Keep cash above 10% of portfolio"
        ),
    },
]

# Mock prices — written directly to Redis so the dashboard shows live data
# without needing a paid Polygon API plan. Matches frontend mock-data.ts values.
MOCK_PRICES = {
    "NVDA": {"price": 595.10, "change_pct":  2.14, "change_abs":  12.50, "open": 582.60, "high": 598.40, "low": 580.10, "volume": 42_800_000, "vwap": 589.30},
    "AAPL": {"price": 184.25, "change_pct":  0.61, "change_abs":   1.12, "open": 183.13, "high": 185.10, "low": 182.50, "volume": 55_200_000, "vwap": 183.90},
    "META": {"price": 510.55, "change_pct":  1.38, "change_abs":   6.95, "open": 503.60, "high": 512.80, "low": 502.10, "volume": 18_600_000, "vwap": 507.20},
    "MSFT": {"price": 422.80, "change_pct":  0.88, "change_abs":   3.70, "open": 419.10, "high": 424.50, "low": 418.30, "volume": 22_100_000, "vwap": 421.30},
    "TSLA": {"price": 178.90, "change_pct": -1.42, "change_abs":  -2.58, "open": 181.48, "high": 182.30, "low": 177.60, "volume": 98_500_000, "vwap": 179.80},
    "AMZN": {"price": 182.30, "change_pct":  0.97, "change_abs":   1.75, "open": 180.55, "high": 183.20, "low": 179.80, "volume": 38_400_000, "vwap": 181.50},
    "GOOGL": {"price": 170.25, "change_pct":  1.22, "change_abs":   2.05, "open": 168.20, "high": 171.00, "low": 167.90, "volume": 25_300_000, "vwap": 169.60},
    "AMD":  {"price": 152.40, "change_pct": -0.53, "change_abs":  -0.81, "open": 153.21, "high": 154.10, "low": 151.80, "volume": 44_700_000, "vwap": 152.90},
    "PLTR": {"price":  22.85, "change_pct":  3.17, "change_abs":   0.70, "open":  22.15, "high":  23.10, "low":  22.00, "volume": 82_100_000, "vwap":  22.60},
    "CRM":  {"price": 287.60, "change_pct":  0.74, "change_abs":   2.10, "open": 285.50, "high": 289.00, "low": 284.80, "volume": 12_900_000, "vwap": 287.00},
}

# Organic growth curve — same values as frontend mock-data.ts
_CURVE = [
    0.000, 0.010, 0.015, 0.030, 0.025, 0.040, 0.055, 0.040, 0.060,
    0.070, 0.065, 0.080, 0.075, 0.090, 0.100, 0.095, 0.105, 0.120,
    0.115, 0.130, 0.140, 0.135, 0.145, 0.160, 0.155, 0.165, 0.180,
    0.175, 0.190, 0.210, 0.205, 0.215, 0.230, 0.225, 0.240, 0.255,
    0.245, 0.260, 0.280, 0.270, 0.285, 0.300, 0.295, 0.310, 0.325,
    0.315, 0.330, 0.350, 0.345, 0.355, 0.370, 0.365, 0.380, 0.400,
    0.390, 0.410, 0.420, 0.415, 0.430, 0.450, 0.440, 0.455, 0.470,
    0.465, 0.480, 0.500, 0.490, 0.510, 0.530, 0.520, 0.535, 0.550,
    0.545, 0.560, 0.580, 0.570, 0.585, 0.600, 0.595, 0.620, 0.640,
    0.630, 0.645, 0.660, 0.680, 0.700, 0.720, 0.750, 0.800, 0.900, 1.000,
]


# ─── Command ──────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seed the database with realistic demo portfolio data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=None,
            help="Email of the user to seed (default: first superuser, then first user)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing portfolio/journal data for this user first",
        )

    def handle(self, *args, **options):
        user = self._resolve_user(options["email"])
        self.stdout.write(f"\nSeeding data for: {self.style.SUCCESS(user.email)}\n")

        if options["reset"]:
            self._reset(user)

        self._seed_positions(user)
        self._seed_alerts(user)
        self._seed_watchlist(user)
        self._seed_journal(user)
        self._seed_snapshots(user)
        self._seed_prices()

        self.stdout.write(self.style.SUCCESS(
            "\nDone! Open http://localhost:3000 and log in to explore the demo data."
        ))

    # ─── Steps ────────────────────────────────────────────────

    def _resolve_user(self, email):
        if email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                raise CommandError(
                    f"User '{email}' not found.\n"
                    "Create one first: docker compose exec api python manage.py createsuperuser"
                )
        user = (
            User.objects.filter(is_superuser=True).order_by("id").first()
            or User.objects.order_by("id").first()
        )
        if not user:
            raise CommandError(
                "No users found. Create one first:\n"
                "  docker compose exec api python manage.py createsuperuser"
            )
        return user

    def _reset(self, user):
        self.stdout.write(self.style.WARNING("  Resetting existing data..."))
        JournalEntry.objects.filter(user=user).delete()
        PortfolioSnapshot.objects.filter(user=user).delete()
        Position.objects.filter(user=user).delete()   # cascades Trades
        PriceAlert.objects.filter(user=user).delete()
        Watchlist.objects.filter(user=user).delete()

    def _seed_positions(self, user):
        self.stdout.write("  Positions & Trades:")
        for pd in POSITIONS:
            expiry  = (
                date.today() + timedelta(days=pd["expiry_days_from_now"])
                if pd.get("expiry_days_from_now") else None
            )
            is_open = pd.get("is_open", True)
            pos, created = Position.objects.get_or_create(
                user=user,
                ticker=pd["ticker"],
                asset_type=pd["asset_type"],
                avg_cost=Decimal(pd["avg_cost"]),
                defaults={
                    "quantity": Decimal(pd["quantity"]),
                    "strike":   Decimal(pd["strike"]) if pd.get("strike") else None,
                    "expiry":   expiry,
                    "is_open":  is_open,
                },
            )
            label = f"{pd['ticker']} {pd['asset_type']}"
            if not created:
                self.stdout.write(f"    skip (exists): {label}")
                continue

            # Backdate opened_at (and closed_at for closed positions) —
            # auto_now_add blocks direct assignment at create time.
            backdate = {"opened_at": _dt(pd["opened_days_ago"])}
            if pd.get("closed_days_ago"):
                backdate["closed_at"] = _dt(pd["closed_days_ago"])
            Position.objects.filter(pk=pos.pk).update(**backdate)

            for td in pd.get("trades", []):
                Trade.objects.create(
                    position     = pos,
                    side         = td["side"],
                    quantity     = Decimal(td["qty"]),
                    price        = Decimal(td["price"]),
                    fees         = Decimal(td.get("fees", "0.00")),
                    executed_at  = _dt(td["days_ago"]),
                    realized_pnl = Decimal(td["realized_pnl"]) if td.get("realized_pnl") else None,
                    notes        = td.get("notes", ""),
                )
            self.stdout.write(self.style.SUCCESS(f"    created: {label}"))

    def _seed_alerts(self, user):
        self.stdout.write("  Alerts:")
        for ad in ALERTS:
            triggered_at = _dt(ad["triggered_days_ago"]) if ad.get("triggered_days_ago") is not None else None
            triggered_price = Decimal(ad["triggered_price"]) if ad.get("triggered_price") else None
            _, created = PriceAlert.objects.get_or_create(
                user=user,
                ticker=ad["ticker"],
                condition=ad["condition"],
                target_price=Decimal(ad["target_price"]),
                defaults={
                    "is_active":       ad["is_active"],
                    "triggered_at":    triggered_at,
                    "triggered_price": triggered_price,
                },
            )
            status = "created" if created else "skip (exists)"
            style  = self.style.SUCCESS if created else str
            self.stdout.write(style(
                f"    {status}: {ad['ticker']} {ad['condition']} ${ad['target_price']}"
            ))

    def _seed_watchlist(self, user):
        self.stdout.write("  Watchlist:")
        for wd in WATCHLIST:
            _, created = Watchlist.objects.get_or_create(
                user=user, ticker=wd["ticker"],
                defaults={"notes": wd["notes"]},
            )
            status = "created" if created else "skip (exists)"
            style  = self.style.SUCCESS if created else str
            self.stdout.write(style(f"    {status}: {wd['ticker']}"))

    def _seed_journal(self, user):
        self.stdout.write("  Journal entries:")
        for jd in JOURNAL:
            if JournalEntry.objects.filter(user=user, title=jd["title"]).exists():
                self.stdout.write(f"    skip (exists): {jd['title'][:55]}")
                continue
            entry = JournalEntry.objects.create(
                user=user,
                title=jd["title"],
                body=jd["body"],
                ticker=jd["ticker"],
                tags=jd["tags"],
                ai_generated=jd["ai_generated"],
            )
            JournalEntry.objects.filter(pk=entry.pk).update(
                created_at=_dt(jd["days_ago"]),
                updated_at=_dt(max(jd["days_ago"] - 10, 0)),
            )
            self.stdout.write(self.style.SUCCESS(f"    created: {jd['title'][:55]}"))

    def _seed_prices(self):
        """Write mock quotes to Redis so the dashboard shows P&L without Polygon API."""
        self.stdout.write("  Redis prices (mock quotes):")
        cache = QuoteCache()
        for ticker, quote in MOCK_PRICES.items():
            cache.set(ticker, quote)
        self.stdout.write(self.style.SUCCESS(
            f"    cached {len(MOCK_PRICES)} quotes → Redis (TTL 120s; Celery will refresh after that)"
        ))

    def _seed_snapshots(self, user):
        self.stdout.write("  Portfolio snapshots (90-day P&L history):")
        cost_basis = Decimal("63481.00")
        end_value  = Decimal("96475.00")
        days       = 90
        created_count = 0

        for i in range(days):
            snap_date = _date(days - 1 - i)
            t   = Decimal(str(_CURVE[i]))
            mv  = cost_basis + (end_value - cost_basis) * t
            pnl = mv - cost_basis
            pnl_pct  = (pnl / cost_basis * Decimal("100")).quantize(Decimal("0.0001"))
            realized = Decimal("0") if i < 30 else Decimal(str((i - 30) * 42))

            _, created = PortfolioSnapshot.objects.get_or_create(
                user=user,
                date=snap_date,
                defaults={
                    "total_cost_basis":         cost_basis.quantize(Decimal("0.0001")),
                    "total_market_value":       mv.quantize(Decimal("0.0001")),
                    "total_unrealized_pnl":     pnl.quantize(Decimal("0.0001")),
                    "total_unrealized_pnl_pct": pnl_pct,
                    "total_realized_pnl":       realized.quantize(Decimal("0.0001")),
                    "positions_count":          6,
                    "prices_captured":          True,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"    created {created_count} snapshots"
            + (f" ({days - created_count} already existed)" if created_count < days else "")
        ))
