"""Tests for /health/ endpoint."""

import pytest


@pytest.mark.django_db
class TestHealthCheck:

    def test_endpoint_exists(self, client):
        resp = client.get("/health/")
        assert resp.status_code in (200, 503)
        assert resp["content-type"].startswith("application/json")

    def test_response_shape(self, client):
        data = client.get("/health/").json()
        assert "status"   in data
        assert "services" in data
        assert data["status"] in ("healthy", "degraded")

    def test_all_services_reported(self, client):
        services = client.get("/health/").json()["services"]
        assert "postgres"      in services
        assert "redis"         in services
        assert "elasticsearch" in services
        assert "celery"        in services

    def test_postgres_is_ok_in_tests(self, client):
        resp = client.get("/health/")
        assert resp.json()["services"]["postgres"] == "ok"

    def test_does_not_require_auth(self, client):
        resp = client.get("/health/")
        assert resp.status_code != 401
