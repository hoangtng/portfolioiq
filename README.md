# PortfolioIQ

> Track your portfolio, research stocks and options, set price alerts, and build a searchable knowledge base of your own trade notes — all in one place.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0-092E20?style=flat-square&logo=django&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.13-005571?style=flat-square&logo=elasticsearch&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)

---

## Overview

PortfolioIQ is a personal investment dashboard built for serious retail traders who want one place to track positions, monitor live prices, research options, and keep a searchable record of every trade decision they've ever made.

The backend is a Django REST API backed by PostgreSQL, a Redis quote cache populated every 60 seconds by a Celery worker, Elasticsearch for full-text journal search, and an AI layer powered by Claude. The frontend is a Next.js 14 app with a glass morphism trading UI. All six services — Django, Postgres, Redis, Elasticsearch, Celery worker, and Celery Beat — start with a single `make dev`.

The project is built phase by phase. Phase 0 is complete. Phase 1 and 2 are in progress.

---

## Features

### Phase 0 — Foundation ✅

- Custom `User` model with email login and Google OAuth
- JWT authentication (simplejwt) with automatic token refresh
- `/health/` endpoint verifying all four services are reachable
- Docker Compose with health checks and `depends_on` ordering
- `Makefile` shortcuts for every common dev task

### Phase 1 — Core Portfolio *(in progress)*

- **Portfolio summary** — all open positions enriched with live prices from Redis, aggregate cost basis, market value, and unrealized P&L in one response
- **Positions** — track stocks and options (calls/puts with strike, expiry, contract multiplier); weighted average cost recalculated on every buy; realized P&L on sells; position auto-closes when quantity hits zero
- **Trade history** — every execution stored with price, quantity, fees, and realized P&L
- **Price alerts** — above/below conditions checked every 60 seconds by Celery; Telegram notification sent on trigger; alert deactivated after firing
- **Options chain** — full chain with Greeks (Δ, Γ, Θ, V), IV, open interest, and break-even via Massive API; cursor-based pagination handled automatically
- **Watchlist** — follow tickers without holding a position; prices fetched alongside portfolio
- **Live price feed** — Celery Beat calls Massive API every 60 seconds for all portfolio and watchlist tickers in one request; writes to Redis with 120s TTL; graceful fallback to previous-close endpoint on free tier (403)

### Phase 2 — Journal + AI *(in progress)*

- Trade journal stored in PostgreSQL, mirrored to Elasticsearch via `post_save` signal
- Full-text search across title and body, title boosted 2×, fuzzy matching, highlighted snippets, Postgres fallback if Elasticsearch is down
- AI orchestra: three Claude agents (portfolio analyst, journal writer, portfolio chat) dispatched by a central router
- Agents pull live portfolio data from Postgres + Redis automatically — no manual payload needed
- AI-generated journal entries saved to the database and auto-indexed to Elasticsearch
- Telegram bot: `/analyze`, `/chat`, `/journal` commands from your phone

---

## Architecture


![PortfolioIQ system architecture](./portfolioiq_full_architecture.svg)


---

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Authentication | simplejwt · google-auth |
| Database | PostgreSQL 16 |
| Cache + broker | Redis 7 |
| Search | Elasticsearch 8.13 + django-elasticsearch-dsl |
| Task queue | Celery 5 + Celery Beat + django-celery-beat |
| Market data | Massive API (formerly Polygon.io) |
| AI agents | Anthropic Claude (claude-sonnet-4-6) |
| Notifications | Telegram Bot API |
| Frontend | Next.js 14 App Router + TypeScript |
| Styling | Tailwind CSS — custom glass morphism design tokens |
| Charts | Recharts |
| Containers | Docker + Docker Compose |
| Linting | Ruff |
| Testing | pytest + pytest-django |

---

## Project structure

```
portfolioiq/                       ← Django backend
├── config/
│   ├── settings.py                ← reads .env via django-environ
│   ├── urls.py                    ← root URL router
│   ├── celery.py                  ← Celery app + autodiscovery
│   └── wsgi.py
│
├── apps/
│   ├── users/                     ← Phase 0
│   │   ├── models.py              ← custom User with telegram_chat_id
│   │   ├── serializers.py         ← email login + Google OAuth serializers
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── google.py              ← verify Google ID token, find-or-create user
│   │
│   ├── portfolio/                 ← Phase 1
│   │   ├── models.py              ← Position, Trade, PriceAlert, Watchlist
│   │   ├── serializers.py         ← PositionSerializer pulls live price from Redis
│   │   ├── views.py               ← 10 API endpoints
│   │   ├── urls.py
│   │   ├── tasks.py               ← fetch_quotes, check_price_alerts
│   │   ├── admin.py
│   │   ├── services/
│   │   │   ├── cache.py           ← QuoteCache — get / set / get_many / warm
│   │   │   ├── polygon.py         ← MassiveClient — snapshot, prev close, options chain
│   │   │   └── portfolio.py       ← PortfolioService — get_summary, record_trade
│   │   ├── migrations/
│   │   └── management/commands/
│   │       └── setup_periodic_tasks.py
│   │
│   ├── journal/                   ← Phase 2
│   │   ├── models.py              ← JournalEntry + post_save/post_delete ES signals
│   │   ├── documents.py           ← ES index mapping (text vs keyword fields)
│   │   ├── services.py            ← JournalSearchService — multi_match, highlights
│   │   ├── serializers.py
│   │   ├── views.py               ← list/create · detail · search
│   │   ├── urls.py
│   │   ├── migrations/
│   │   └── management/commands/
│   │       └── build_search_index.py
│   │
│   └── ai/                        ← Phase 2
│       ├── agents.py              ← 3 Claude agents + central router
│       ├── prompts.py             ← per-agent system prompts
│       ├── tasks.py               ← run_ai_agent (async), handle_telegram_message
│       ├── telegram.py            ← TelegramService, command parser
│       ├── views.py               ← analyze · journal · chat · result · webhook
│       └── urls.py
│
├── tests/
│   ├── test_health.py
│   ├── test_auth.py
│   ├── test_portfolio.py          ← models, service logic, API endpoints, Celery tasks
│   └── test_phase2.py             ← journal CRUD, ES signals, AI saving
│
├── docker-compose.yml             ← 6 services with health checks
├── Dockerfile
├── Makefile
├── requirements.txt
├── pytest.ini
└── .env.example

portfolioiq-frontend/              ← Next.js 14 frontend
├── src/
│   ├── app/
│   │   ├── layout.tsx             ← AuthContext + JWT refresh + Google Fonts
│   │   ├── page.tsx               ← redirect to /dashboard or /login
│   │   ├── login/page.tsx         ← floating orbs, glass form
│   │   ├── dashboard/             ← summary cards, 30-day curve, positions overview
│   │   ├── positions/             ← glass cards, sparklines, trade history, add modal
│   │   ├── alerts/                ← active/triggered tabs, live pulse indicator
│   │   ├── options/               ← chain table, Greeks, ITM rows highlighted
│   │   ├── watchlist/             ← live price grid with trend arrows
│   │   └── journal/               ← stub, Phase 2
│   ├── components/layout/
│   │   └── Sidebar.tsx            ← nav with active states, user info
│   ├── lib/
│   │   ├── api.ts                 ← typed API client, auto refresh on 401
│   │   └── utils.ts               ← fmtCurrency, fmtPnl, pnlClass, greekColor
│   └── types/index.ts             ← interfaces matching every API response
├── tailwind.config.ts             ← void/nebula/aurora/glass design tokens
├── package.json
└── .env.local.example
```

---

## Getting started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — runs all backend services
- Node.js 18+ — frontend only
- A free [Massive API key](https://massive.com/dashboard/signup)

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/portfolioiq.git
cd portfolioiq
cp .env.example .env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Minimum `.env` values to fill in:

```env
DJANGO_SECRET_KEY=paste-key-here
POLYGON_API_KEY=your_massive_api_key
```

### 2. Start all services

```bash
make dev
```

First run pulls Docker images for Postgres, Elasticsearch, and Redis — takes 3–5 minutes. After that, startup is under 10 seconds.

### 3. Set up the database

```bash
make migrate
make createsuperuser
docker compose exec api python manage.py setup_periodic_tasks
```

`setup_periodic_tasks` registers `fetch_quotes` and `check_price_alerts` in the database scheduler so Celery Beat runs them every 60 seconds.

### 4. Verify

```bash
curl http://localhost:8000/health/
```

```json
{
  "status": "healthy",
  "services": {
    "postgres": "ok",
    "redis": "ok",
    "elasticsearch": "green",
    "celery": "ok"
  }
}
```

### 5. Start the frontend

```bash
cd portfolioiq-frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## API reference

### Auth — `/api/v1/auth/`

| Method | Path | Description |
|---|---|---|
| `POST` | `register/` | Create account |
| `POST` | `token/` | Email + password → JWT pair |
| `POST` | `token/refresh/` | Rotate access token |
| `POST` | `token/verify/` | Validate an access token |
| `POST` | `google/` | Google ID token → JWT pair |
| `GET` | `me/` | Current user |

### Portfolio — `/api/v1/portfolio/`

| Method | Path | Description |
|---|---|---|
| `GET` | `summary/` | Positions + live prices + aggregate P&L |
| `GET` `POST` | `positions/` | List · create |
| `GET` `PATCH` `DELETE` | `positions/{id}/` | Retrieve · update · delete |
| `GET` `POST` | `positions/{id}/trades/` | Trade history · record trade |
| `GET` `POST` | `alerts/` | List · create |
| `DELETE` | `alerts/{id}/` | Remove |
| `GET` | `quote/{ticker}/` | Live quote |
| `GET` | `options/{ticker}/` | Options chain with Greeks |
| `GET` `POST` | `watchlist/` | List · add ticker |
| `DELETE` | `watchlist/{id}/` | Remove ticker |

### Journal — `/api/v1/journal/` *(Phase 2)*

| Method | Path | Description |
|---|---|---|
| `GET` `POST` | `` | List · create entry |
| `GET` `PATCH` `DELETE` | `{id}/` | Retrieve · edit · delete |
| `GET` | `search/?q=...` | Full-text search with highlights |

### AI — `/api/v1/ai/` *(Phase 2)*

| Method | Path | Description |
|---|---|---|
| `POST` | `analyze/` | Queue portfolio analysis → `task_id` |
| `POST` | `journal/` | Generate + save journal entry → `task_id` |
| `POST` | `chat/` | Synchronous portfolio Q&A |
| `GET` | `result/{task_id}/` | Poll async task result |
| `POST` | `telegram/webhook/` | Telegram push receiver |

### System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health/` | Service health check |
| `GET` | `/admin/` | Django Admin |

---

## Development

```bash
make dev              # start all 6 services
make down             # stop everything
make build            # rebuild images without cache
make migrate          # run pending migrations
make makemigrations   # generate migrations after model changes
make test             # run all tests
make lint             # ruff linter
make shell            # Django shell inside the container
make logs             # tail all service logs
make logs-api         # Django logs only
make logs-worker      # Celery worker logs
make createsuperuser  # create an admin user
```

### Tests

```bash
make test
```

```
tests/test_health.py::test_health_endpoint_exists              PASSED
tests/test_health.py::test_health_response_has_all_services    PASSED
tests/test_auth.py::test_register                              PASSED
tests/test_auth.py::test_obtain_token_with_email               PASSED
tests/test_auth.py::test_obtain_token_wrong_password           PASSED
tests/test_auth.py::test_me_requires_auth                      PASSED
tests/test_auth.py::test_me_returns_user                       PASSED
tests/test_portfolio.py::TestPositionModel::test_cost_basis_stock              PASSED
tests/test_portfolio.py::TestPositionModel::test_unrealized_pnl_profit         PASSED
tests/test_portfolio.py::TestPortfolioService::test_record_buy_updates_avg_cost PASSED
tests/test_portfolio.py::TestPortfolioService::test_sell_all_closes_position    PASSED
tests/test_portfolio.py::TestCeleryTasks::test_fetch_quotes_free_tier_fallback  PASSED
... 25 passed
```

---

## Market data

This project uses [Massive](https://massive.com) (formerly Polygon.io, rebranded 2025) for stock and options data.

| Endpoint | Plan | Used for |
|---|---|---|
| `GET /v2/snapshot/locale/us/markets/stocks/tickers` | Starter+ ($29/mo) | Batch price fetch for all tickers in one call |
| `GET /v2/aggs/ticker/{t}/prev` | Free | Previous-close fallback |
| `GET /v3/snapshot/options/{ticker}` | Starter+ ($29/mo) | Options chain with Greeks |

**Free tier:** `fetch_quotes` automatically detects a 403 from the snapshot endpoint and falls back to `get_previous_close_many()`. You get end-of-day prices instead of intraday, but the dashboard always shows real numbers. `PolygonClient` is kept as an alias for `MassiveClient` so no existing imports break.

---

## Environment variables

| Variable | Required from | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Phase 0 | Long random string — never commit |
| `DJANGO_DEBUG` | Phase 0 | `True` for dev, `False` for prod |
| `DATABASE_URL` | Phase 0 | `postgres://user:pass@host:port/db` |
| `REDIS_URL` | Phase 0 | `redis://host:port/0` |
| `ELASTICSEARCH_URL` | Phase 0 | `http://host:9200` |
| `CELERY_BROKER_URL` | Phase 0 | `redis://host:port/1` |
| `POLYGON_API_KEY` | Phase 1 | Massive API key — free at massive.com |
| `ANTHROPIC_API_KEY` | Phase 2 | Claude API key — console.anthropic.com |
| `TELEGRAM_BOT_TOKEN` | Phase 2 | From @BotFather on Telegram |
| `GOOGLE_OAUTH_CLIENT_ID` | Phase 0 | Google Cloud Console |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Phase 0 | Google Cloud Console |

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| **Phase 0** | ✅ Complete | Docker, auth (email + Google OAuth), JWT, health check |
| **Phase 1** | 🔨 In progress | Positions, trades, P&L, alerts, options chain, Massive API, Celery price feed, Next.js UI |
| **Phase 2** | 📋 Planned | Trade journal, Elasticsearch search, Claude AI agents, Telegram bot |
| **Phase 3** | 📋 Planned | P&L history, portfolio analytics charts, options screener |
| **Phase 4** | 📋 Planned | Production deployment, GitHub Actions CI/CD |

---

## License

MIT — see [LICENSE](LICENSE).
