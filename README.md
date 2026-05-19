<div align="center">

# PortfolioIQ

**An AI analyst that actually knows your portfolio.**

Track positions in real time. Research options. Set price alerts. Ask Claude anything about your holdings — grounded in your real data, not a chatbot reading headlines.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.13-005571?style=flat-square&logo=elasticsearch&logoColor=white)](https://www.elastic.co)
[![Claude](https://img.shields.io/badge/Powered_by-Claude-D4A373?style=flat-square)](https://anthropic.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

[**Live Demo**](#) · [**Documentation**](#api-reference) · [**Deploy to AWS**](./docs/DEPLOY-AWS.md) · [**Report a bug**](https://github.com/hoangtng/PortfolioIQ/issues)

</div>

---

## About

PortfolioIQ is a full-stack investment dashboard for retail traders. The differentiator: an AI layer powered by Claude that sees your real positions, costs, and exposure — so when you ask "what's my biggest concentration risk?" you get a specific answer about your actual book, not a generic web search dressed up as advice.

The backend is a Django REST API with PostgreSQL, a Redis quote cache refreshed every 60 seconds by Celery, Elasticsearch for full-text journal search, and three Claude-powered agents (portfolio analyst, journal writer, conversational chat). The frontend is a Next.js 14 app with a trading-terminal aesthetic. Everything starts with one `make dev` command.

> [!NOTE]
> Built as a SaaS product to demonstrate production-grade engineering: multi-service Docker orchestration, async task queues, full-text search, real-time data, AI agent design, and a custom design system. Code is MIT-licensed, self-host, or contribute.

---

## Highlights

| | |
|---|---|
| 🤖 **AI Portfolio Analyst** | Three specialized Claude agents — analyst, journal writer, conversational chat — automatically pull live portfolio context from Postgres + Redis. One click, full-portfolio analysis with concentration risk, expiry exposure, and rebalancing suggestions specific to your book. |
| 📈 **Real-Time Position Tracking** | Stocks and options (calls/puts, strikes, expiries). Weighted average cost recalculated on every buy. Realized P&L on sells. Auto-closes when quantity hits zero. Dashboard polls every 20 seconds with smooth value-flash animations. |
| 🎯 **Smart Price Alerts** | Above/below conditions checked every 60 seconds. Telegram push the moment your level hits. Alert auto-deactivates after firing. Setup in seconds. |
| 📊 **Pro-Grade Options Data** | Full chain with Greeks (Δ, Γ, Θ, V), implied volatility, open interest, and break-even auto-computed. Filter by expiry, strike, or moneyness. |
| 📝 **Searchable Trade Journal** | AI writes structured entries for every trade. Elasticsearch full-text search with title boost, fuzzy matching, and highlighted snippets. Postgres fallback if ES is down. |
| 💬 **Telegram Bot** | `/analyze` for portfolio analysis, `/chat` for Q&A, `/journal` for trade entries — all from your phone. |
| 📉 **Live P&L Chart** | Interactive line chart combining historical snapshots with a live "today" point. Toggle between portfolio value and P&L. 7d / 30d / 90d range. |

---

## Architecture

[![PortfolioIQ system architecture](./architecture.svg)](./architecture.svg)

The system runs as **six containerized services** orchestrated by Docker Compose:

| Service | Role |
|---|---|
| `api` | Django + DRF, JWT auth, REST endpoints |
| `worker` | Celery worker — quote refresh, alert checks, AI tasks |
| `beat` | Celery Beat — schedules background tasks (DB-backed scheduler) |
| `postgres` | Primary data store — users, positions, trades, journal |
| `redis` | Quote cache (60s refresh), Celery broker, session store |
| `elasticsearch` | Full-text search index for journal entries |

The frontend is a separate Next.js 14 app deployable to Vercel or self-hosted. Auth is JWT with automatic refresh. The dashboard polls the live `/portfolio/summary` endpoint every 20 seconds and renders smooth value-flash animations when numbers change.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend framework** | Django 5 · Django REST Framework |
| **Authentication** | simplejwt · google-auth |
| **Database** | PostgreSQL 16 |
| **Cache + broker** | Redis 7 |
| **Search** | Elasticsearch 8.13 · django-elasticsearch-dsl |
| **Task queue** | Celery 5 · Celery Beat · django-celery-beat |
| **Market data** | Massive API (formerly Polygon.io) · yfinance fallback |
| **AI agents** | Anthropic Claude (claude-sonnet-4-6) |
| **Notifications** | Telegram Bot API |
| **Frontend framework** | Next.js 14 (App Router) · TypeScript |
| **Styling** | Tailwind CSS · custom trading-terminal design tokens |
| **Charts** | Custom SVG (interactive P&L chart) · Recharts (analytics) |
| **Containers** | Docker · Docker Compose |
| **Code quality** | Ruff · ESLint |
| **Testing** | pytest · pytest-django · Testing Library |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) for the backend services
- Node.js 18+ for the frontend
- A free [Massive API key](https://massive.com/dashboard/signup) (or use the free yfinance fallback)
- Optional: [Anthropic API key](https://console.anthropic.com) for AI features, Telegram bot token from [@BotFather](https://t.me/BotFather)

### 1. Clone and configure

```bash
git clone https://github.com/hoangtng/PortfolioIQ.git
cd PortfolioIQ
cp .env.example .env
```

Generate a Django secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Minimum `.env` values to set:

```bash
DJANGO_SECRET_KEY=paste-key-here
POLYGON_API_KEY=your_massive_api_key       # optional — uses yfinance if blank
ANTHROPIC_API_KEY=sk-ant-...               # for AI features
TELEGRAM_BOT_TOKEN=123456:ABC...           # for Telegram bot
```

### 2. Start all services

```bash
make dev
```

First run pulls Postgres, Redis, and Elasticsearch images — takes 3–5 minutes. Subsequent startups are under 10 seconds.

### 3. Initialize the database

```bash
make migrate
make createsuperuser
docker compose exec api python manage.py setup_periodic_tasks
```

`setup_periodic_tasks` registers `fetch_quotes` and `check_price_alerts` so Celery Beat runs them every 60 seconds.

### 4. Verify everything is up

```bash
curl http://localhost:8000/health/
```

```json
{
  "status": "healthy",
  "services": {
    "postgres":      "ok",
    "redis":         "ok",
    "elasticsearch": "green",
    "celery":        "ok"
  }
}
```

### 5. Start the frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Log in with the superuser you created.

---

## Demo Data

To explore the app without manually creating positions, seed realistic demo data:

```bash
docker compose exec api python manage.py seed_demo_data
```

This creates a demo user with 10 mixed positions (stocks + options, some open/closed), trade history, journal entries, watchlist, price alerts, and 90 days of portfolio snapshots. Login credentials:

```
Email:    ethan@demo.com
Password: demo1234
```

Options:

```bash
python manage.py seed_demo_data --users 3            # multiple demo users
python manage.py seed_demo_data --positions 20      # more positions per user
python manage.py seed_demo_data --days 180          # longer history
python manage.py seed_demo_data --reset             # wipe demo data and re-seed
```

---

## API Reference

### Auth — `/api/auth/`

| Method | Path | Description |
|---|---|---|
| `POST` | `register/` | Create account with email + password |
| `POST` | `token/` | Email + password → JWT access/refresh pair |
| `POST` | `token/refresh/` | Rotate access token |
| `POST` | `token/verify/` | Validate an access token |
| `POST` | `google/` | Google ID token → JWT pair |
| `GET` | `me/` | Current user |

### Portfolio — `/api/portfolio/`

| Method | Path | Description |
|---|---|---|
| `GET` | `summary/` | Open positions + live prices + aggregate P&L |
| `GET` `POST` | `positions/` | List · create |
| `GET` `PATCH` `DELETE` | `positions/{id}/` | Retrieve · update · delete |
| `GET` `POST` | `positions/{id}/trades/` | Trade history · record buy or sell |
| `GET` `POST` | `alerts/` | List · create price alert |
| `DELETE` | `alerts/{id}/` | Remove |
| `GET` | `quote/{ticker}/` | Live quote (Redis cache → API fallback) |
| `GET` | `options/{ticker}/` | Options chain with Greeks |
| `GET` `POST` | `watchlist/` | List · add ticker |
| `DELETE` | `watchlist/{id}/` | Remove |

### Analytics — `/api/analytics/`

| Method | Path | Description |
|---|---|---|
| `GET` | `history/?days=N` | Portfolio snapshots over the last N days |
| `GET` | `performance/` | Win rate, profit factor, Sharpe-like metrics |

### Journal — `/api/journal/`

| Method | Path | Description |
|---|---|---|
| `GET` `POST` | `` | List · create entry |
| `GET` `PATCH` `DELETE` | `{id}/` | Retrieve · edit · delete |
| `GET` | `search/?q=...` | Elasticsearch full-text search with highlights |

### AI — `/api/ai/`

| Method | Path | Description |
|---|---|---|
| `POST` | `analyze/` | Queue portfolio analysis → returns `task_id` |
| `POST` | `journal/` | Generate + save journal entry → returns `task_id` |
| `POST` | `chat/` | Synchronous portfolio Q&A |
| `GET` | `result/{task_id}/` | Poll an async task result |
| `POST` | `telegram/setup/` | Register webhook URL with Telegram |
| `POST` | `telegram/webhook/` | Inbound webhook receiver (Telegram → us) |

### System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health/` | Service health check |
| `GET` | `/admin/` | Django admin |

---

## Project Structure

```
PortfolioIQ/
├── backend/                       # Django project root
│   ├── core/                      # config, settings, urls, celery, wsgi
│   ├── apps/
│   │   ├── users/                 # custom User, JWT auth, Google OAuth
│   │   ├── portfolio/             # positions, trades, alerts, market data
│   │   │   ├── models.py          # Position · Trade · PriceAlert · Watchlist
│   │   │   ├── services/
│   │   │   │   ├── cache.py       # QuoteCache (Redis)
│   │   │   │   ├── polygon.py     # MassiveClient with yfinance fallback
│   │   │   │   └── portfolio.py   # PortfolioService — summary, record_trade
│   │   │   ├── tasks.py           # fetch_quotes · check_price_alerts
│   │   │   └── management/commands/
│   │   │       ├── setup_periodic_tasks.py
│   │   │       └── seed_demo_data.py
│   │   │
│   │   ├── analytics/             # Phase 3
│   │   │   ├── models.py          # PortfolioSnapshot · PositionSnapshot
│   │   │   ├── services.py        # snapshot generation, performance metrics
│   │   │   └── tasks.py           # take_snapshot (daily 21:00 UTC)
│   │   │
│   │   ├── journal/               # Phase 2
│   │   │   ├── models.py          # JournalEntry with ES signals
│   │   │   ├── documents.py       # ES index mapping
│   │   │   └── services.py        # JournalSearchService
│   │   │
│   │   └── ai/                    # Phase 2
│   │       ├── agents.py          # 3 Claude agents + route() dispatcher
│   │       ├── prompts.py         # per-agent system prompts
│   │       ├── telegram.py        # TelegramService + command parser
│   │       └── tasks.py           # async agent execution
│   │
│   ├── tests/                     # pytest test suite
│   ├── docker-compose.yml         # 6 services with health checks
│   ├── Dockerfile                 # multi-stage production build
│   └── Makefile                   # dev workflow shortcuts
│
├── frontend/                      # Next.js 14 app
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # marketing landing page
│   │   │   ├── login/             # auth
│   │   │   ├── register/
│   │   │   ├── dashboard/         # live portfolio, P&L chart, today's change
│   │   │   ├── positions/         # detail + close modal
│   │   │   ├── alerts/            # active/triggered tabs
│   │   │   ├── options/           # chain table with Greeks
│   │   │   ├── watchlist/
│   │   │   ├── journal/
│   │   │   └── analytics/
│   │   ├── components/
│   │   │   ├── dashboard/PnLChart.tsx   # interactive line chart
│   │   │   └── ui/LiveStatus.tsx        # market status + refresh
│   │   ├── lib/
│   │   │   ├── api.ts             # typed API client with token refresh
│   │   │   ├── use-polling.ts     # generic polling hook
│   │   │   ├── use-value-flash.ts # green/red flash on value change
│   │   │   └── utils.ts           # market status, formatting, helpers
│   │   └── types/index.ts
│   ├── tailwind.config.ts         # trading-terminal design tokens
│   └── next.config.js
│
├── docs/
│   ├── DEPLOY-AWS.md              # step-by-step AWS deployment guide
│   └── architecture.md
│
├── docker-compose.prod.yml        # production stack
├── nginx/nginx.conf               # reverse proxy + Cloudflare real-IP
└── scripts/
    ├── ec2-setup.sh               # one-shot EC2 bootstrap
    ├── deploy.sh                  # pull + rebuild + restart
    └── backup.sh                  # daily Postgres → S3
```

---

## Deployment

PortfolioIQ is designed to deploy in two halves:

| Component | Where | Why |
|---|---|---|
| **Backend** (Django + Celery + Postgres + Redis + ES) | AWS EC2 t3.medium | Multi-service stack benefits from a single VM, ~$30/mo |
| **Frontend** (Next.js) | Vercel free tier | Edge CDN, automatic preview deploys, $0 |

Full step-by-step guide in [`docs/DEPLOY-AWS.md`](./docs/DEPLOY-AWS.md). Includes:

- EC2 + security group setup
- Docker installation script
- Cloudflare DNS + free SSL
- Daily Postgres backups to S3
- Three deployment paths (single EC2 → RDS + ElastiCache → ECS Fargate)
- Cost optimization tips

Total monthly cost at <100 users: **~$32**.

```bash
# After AWS prerequisites are in place:
bash scripts/ec2-setup.sh
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Development

```bash
make dev              # start all 6 services
make down             # stop everything
make build            # rebuild images without cache
make migrate          # run pending migrations
make makemigrations   # generate migrations after model changes
make test             # run the full test suite
make lint             # ruff linter
make shell            # Django shell inside the container
make logs             # tail all service logs
make logs-api         # Django logs only
make logs-worker      # Celery worker logs
make createsuperuser  # create an admin user
```

### Testing

```bash
make test
```

```
tests/test_health.py::test_health_endpoint_exists              PASSED
tests/test_auth.py::test_register                              PASSED
tests/test_auth.py::test_obtain_token_with_email               PASSED
tests/test_portfolio.py::TestPositionModel::test_cost_basis    PASSED
tests/test_portfolio.py::TestPortfolioService::test_record_buy PASSED
tests/test_portfolio.py::TestCeleryTasks::test_fetch_quotes    PASSED
tests/test_phase2.py::test_journal_creates_and_indexes_to_es   PASSED
tests/test_phase2.py::test_ai_agent_saves_journal_entry        PASSED
...
27 passed in 4.83s
```

---

## Market Data

PortfolioIQ supports two market data providers, switchable via env var:

| Provider | Tier | Stocks | Options | Real-time |
|---|---|---|---|---|
| **Massive** (formerly Polygon.io) | Free | ✅ Previous-close only | ❌ | ❌ |
| **Massive** | Starter ($29/mo) | ✅ Delayed snapshots | ✅ Full chain + Greeks | ❌ |
| **yfinance** (Yahoo) | Free | ✅ Delayed (~15 min) | ✅ Full chain + IV | ❌ |

The `MassiveClient` class auto-falls-back to `get_previous_close_many()` when the snapshot endpoint returns 403 (free tier). For fully-free deployment with options support, swap to the yfinance backend by setting `MARKET_DATA_PROVIDER=yfinance` in your `.env`.

---

## Environment Variables

| Variable | Required from | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Phase 0 | 50-char random string — never commit |
| `DJANGO_DEBUG` | Phase 0 | `True` for dev, `False` for prod |
| `DJANGO_ALLOWED_HOSTS` | Phase 0 | Comma-separated hostnames |
| `DATABASE_URL` | Phase 0 | `postgres://user:pass@host:port/db` |
| `REDIS_URL` | Phase 0 | `redis://host:port/0` |
| `ELASTICSEARCH_URL` | Phase 0 | `http://host:9200` |
| `CELERY_BROKER_URL` | Phase 0 | `redis://host:port/1` |
| `POLYGON_API_KEY` | Phase 1 | Free at [massive.com](https://massive.com) — optional |
| `ANTHROPIC_API_KEY` | Phase 2 | [console.anthropic.com](https://console.anthropic.com) |
| `TELEGRAM_BOT_TOKEN` | Phase 2 | From [@BotFather](https://t.me/BotFather) |
| `GOOGLE_OAUTH_CLIENT_ID` | Phase 0 | Google Cloud Console — optional |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Phase 0 | Google Cloud Console — optional |
| `MARKET_DATA_PROVIDER` | Phase 1 | `massive` (default) or `yfinance` |
| `NEXT_PUBLIC_API_URL` | Phase 0 | Frontend → backend URL (build-time) |

See [`.env.production.example`](./.env.production.example) for the full template with secure defaults.

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| **Phase 0 — Foundation** | ✅ Complete | Docker Compose, custom User, JWT auth, Google OAuth, health check |
| **Phase 1 — Portfolio Core** | ✅ Complete | Positions, trades, P&L, alerts, options chain, live price cache, dashboard UI |
| **Phase 2 — Journal + AI** | ✅ Complete | Trade journal, Elasticsearch search, 3 Claude agents, Telegram bot |
| **Phase 3 — Analytics** | ✅ Complete | Portfolio snapshots, P&L history chart, performance metrics, today's change tracking |
| **Phase 4 — Production** | 🔨 In progress | AWS deployment, CI/CD, monitoring, Sentry integration |
| **Phase 5 — Polish** | 📋 Planned | Mobile responsive, dark/light themes, accessibility audit, English/Vietnamese i18n |

---

## Contributing

This is a personal portfolio project, but contributions, suggestions, and bug reports are welcome. Open an issue first to discuss any larger changes.

```bash
git checkout -b feat/your-feature
make test         # make sure tests still pass
make lint         # ruff + eslint
git commit -m "feat: short description"
```

---

## License

[MIT](./LICENSE) — fork it, self-host it, learn from it. Just don't redistribute trading data scraped from third-party APIs in violation of their terms.

---

## Acknowledgments

- **[Anthropic Claude](https://anthropic.com)** — powers the three AI agents
- **[Massive](https://massive.com)** (formerly Polygon.io) — market data
- **[yfinance](https://github.com/ranaroussi/yfinance)** — free fallback for stocks + options
- **[Cloudflare](https://cloudflare.com)** — free DNS, SSL, CDN, DDoS protection
- **[Vercel](https://vercel.com)** — frontend hosting and edge CDN
- **[shadcn/ui](https://ui.shadcn.com)** — component primitives that inspired the design

---

<div align="center">

**Built by [@hoangtng](https://github.com/hoangtng).**

If this project helped you, consider ⭐ starring the repo.

</div>
