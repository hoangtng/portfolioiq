.PHONY: help dev up down build rebuild logs logs-api logs-worker logs-beat \
        migrate makemigrations shell dbshell createsuperuser test test-fast lint lint-fix \
        format ps clean

# ─── Help ─────────────────────────────────────────────────────
help:  ## Show this help
	@echo "PortfolioIQ — common dev commands\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS=":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── Docker ───────────────────────────────────────────────────
dev: up  ## Alias for `up`

up:  ## Start all services in the background
	docker compose up -d --build
	@echo "\n✅  PortfolioIQ is running at http://localhost:8000"
	@echo "    Health check:  http://localhost:8000/health/"
	@echo "    Django admin:  http://localhost:8000/admin/"

down:  ## Stop all services
	docker compose down

build:  ## Build images
	docker compose build

rebuild:  ## Force-rebuild images without cache
	docker compose build --no-cache

ps:  ## List running containers
	docker compose ps

logs:  ## Tail logs from all services
	docker compose logs -f

logs-api:  ## Tail Django API logs only
	docker compose logs -f api

logs-worker:  ## Tail Celery worker logs
	docker compose logs -f celery_worker

logs-beat:  ## Tail Celery Beat logs
	docker compose logs -f celery_beat

# ─── Django ───────────────────────────────────────────────────
migrate:  ## Apply pending migrations
	docker compose exec api python manage.py migrate

makemigrations:  ## Generate new migrations after model changes
	docker compose exec api python manage.py makemigrations

shell:  ## Open Django shell
	docker compose exec api python manage.py shell

dbshell:  ## Open psql shell
	docker compose exec db psql -U portfolioiq -d portfolioiq

createsuperuser:  ## Create an admin account
	docker compose exec api python manage.py createsuperuser

collectstatic:  ## Collect static files (for production)
	docker compose exec api python manage.py collectstatic --noinput

# ---Seed database---------------------------------------------
seed:
	docker compose exec api python manage.py seed_db --reset


# ─── Quality ──────────────────────────────────────────────────
test:  ## Run the full test suite
	docker compose exec api pytest -v

test-fast:  ## Run tests stopping on first failure
	docker compose exec api pytest -x --ff

lint:  ## Run ruff linter
	docker compose exec api ruff check .

lint-fix:  ## Auto-fix lint issues
	docker compose exec api ruff check . --fix

format:  ## Format code with ruff
	docker compose exec api ruff format .

# ─── Cleanup ──────────────────────────────────────────────────
clean:  ## Remove containers and volumes (destroys all local data)
	docker compose down -v
