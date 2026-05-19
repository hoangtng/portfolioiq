"""
Health check endpoint.

GET /health/
  200 — {"status":"healthy",  "services":{...}}
  503 — {"status":"degraded", "services":{...}}

Used by:
  - Docker compose healthcheck on the api container
  - Frontend loading screen
  - CI smoke test after `make dev`
"""

import logging
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def _check_postgres() -> str:
    try:
        connection.ensure_connection()
        return "ok"
    except Exception as exc:
        logger.warning("Postgres health check failed: %s", exc)
        return f"error: {exc}"


def _check_redis() -> str:
    try:
        cache.set("__health__", "ok", timeout=5)
        return "ok" if cache.get("__health__") == "ok" else "error: unexpected value"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return f"error: {exc}"


def _check_elasticsearch() -> str:
    """
    Elasticsearch is optional until Phase 2.
    Returns "ok" if reachable, "unreachable" otherwise — doesn't fail the
    overall check in early phases.
    """
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch(settings.ELASTICSEARCH_DSL["default"]["hosts"])
        return es.options(request_timeout=2).cluster.health().get("status", "unknown")
    except Exception as exc:
        logger.warning("Elasticsearch health check failed: %s", exc)
        return f"unreachable: {exc}"



def _check_celery() -> str:
    try:
        from config.celery import app as celery_app
        pong = celery_app.control.inspect(timeout=2).ping()
        return "ok" if pong else "no workers responding"
    except Exception as exc:
        logger.warning("Celery health check failed: %s", exc)
        return f"error: {exc}"


@csrf_exempt
@require_GET
def health_check(request):
    services = {
        "postgres":      _check_postgres(),
        "redis":         _check_redis(),
        "elasticsearch": _check_elasticsearch(),
        "celery":        _check_celery(),
    }

    required_ok = "ok" in services["postgres"] and "ok" in services["redis"]
    es_ok = (
        services["elasticsearch"] in ("green", "yellow")
        or services["elasticsearch"].startswith("unreachable")
    )
    celery_ok = "ok" in services["celery"] or "no workers" in services["celery"]
    all_ok = required_ok and es_ok and celery_ok

    return JsonResponse(
        {
            "status":   "healthy" if all_ok else "degraded",
            "services": services,
        },
        status=200 if all_ok else 503,
    )
