"""Tests for email login, register, refresh, logout, /me, change-password."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


# ─── Register ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestRegister:

    def test_creates_user(self, client):
        resp = client.post(
            "/api/auth/register/",
            {"email": "new@example.com", "password": "strongpass123",
             "first_name": "New"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"]      == "new@example.com"
        assert data["first_name"] == "New"
        assert "password" not in data

    def test_email_is_lowercased(self, client):
        resp = client.post(
            "/api/auth/register/",
            {"email": "MIXED@Example.COM", "password": "strongpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["email"] == "mixed@example.com"

    def test_rejects_duplicate_email(self, client, user):
        resp = client.post(
            "/api/auth/register/",
            {"email": "ethan@example.com", "password": "anotherpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_rejects_short_password(self, client):
        resp = client.post(
            "/api/auth/register/",
            {"email": "short@example.com", "password": "abc"},
            content_type="application/json",
        )
        assert resp.status_code == 400


# ─── Email login ──────────────────────────────────────────────

@pytest.mark.django_db
class TestEmailLogin:

    def test_returns_token_pair(self, client, user):
        resp = client.post(
            "/api/auth/token/",
            {"email": "ethan@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access"  in data
        assert "refresh" in data

    def test_email_is_case_insensitive(self, client, user):
        resp = client.post(
            "/api/auth/token/",
            {"email": "Ethan@Example.COM", "password": "testpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_wrong_password(self, client, user):
        resp = client.post(
            "/api/auth/token/",
            {"email": "ethan@example.com", "password": "wrong"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_unknown_email(self, client):
        resp = client.post(
            "/api/auth/token/",
            {"email": "nobody@example.com", "password": "anything"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_inactive_account_rejected(self, client, user):
        user.is_active = False
        user.save()
        resp = client.post(
            "/api/auth/token/",
            {"email": "ethan@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 400


# ─── Token refresh / verify / logout ──────────────────────────

@pytest.mark.django_db
class TestTokenLifecycle:

    def test_refresh_rotates_tokens(self, client, user):
        login = client.post(
            "/api/auth/token/",
            {"email": "ethan@example.com", "password": "testpass123"},
            content_type="application/json",
        ).json()
        refresh = login["refresh"]

        resp = client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["refresh"] != refresh

    def test_verify_endpoint(self, client, access_token):
        resp = client.post(
            "/api/auth/token/verify/",
            {"token": access_token},
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_logout_blacklists_refresh(self, client, user):
        login = client.post(
            "/api/auth/token/",
            {"email": "ethan@example.com", "password": "testpass123"},
            content_type="application/json",
        ).json()
        refresh = login["refresh"]

        resp = client.post(
            "/api/auth/logout/",
            {"refresh": refresh},
            content_type="application/json",
        )
        assert resp.status_code == 200

        retry = client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            content_type="application/json",
        )
        assert retry.status_code == 401


# ─── /me ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMe:

    def test_requires_auth(self, client):
        assert client.get("/api/auth/me/").status_code == 401

    def test_returns_user(self, client, user, auth_headers):
        resp = client.get("/api/auth/me/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "ethan@example.com"

    def test_patch_updates_profile(self, client, user, auth_headers):
        resp = client.patch(
            "/api/auth/me/",
            {"telegram_chat_id": "123456789", "bio": "Trader and coder"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["telegram_chat_id"] == "123456789"
        assert data["bio"]              == "Trader and coder"

    def test_patch_cannot_change_email(self, client, user, auth_headers):
        client.patch(
            "/api/auth/me/",
            {"email": "hacker@example.com"},
            content_type="application/json",
            **auth_headers,
        )
        user.refresh_from_db()
        assert user.email == "ethan@example.com"


# ─── Change password ──────────────────────────────────────────

@pytest.mark.django_db
class TestChangePassword:

    def test_requires_auth(self, client):
        assert client.post(
            "/api/auth/change-password/",
            {},
            content_type="application/json",
        ).status_code == 401

    def test_changes_password(self, client, user, auth_headers):
        resp = client.post(
            "/api/auth/change-password/",
            {
                "current_password": "testpass123",
                "new_password":     "brandnewpass456",
                "confirm_password": "brandnewpass456",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.check_password("brandnewpass456")

    def test_rejects_wrong_current_password(self, client, user, auth_headers):
        resp = client.post(
            "/api/auth/change-password/",
            {
                "current_password": "wrong",
                "new_password":     "brandnewpass456",
                "confirm_password": "brandnewpass456",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 400

    def test_rejects_mismatched_confirm(self, client, user, auth_headers):
        resp = client.post(
            "/api/auth/change-password/",
            {
                "current_password": "testpass123",
                "new_password":     "brandnewpass456",
                "confirm_password": "different456",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 400

    def test_rejects_same_password(self, client, user, auth_headers):
        resp = client.post(
            "/api/auth/change-password/",
            {
                "current_password": "testpass123",
                "new_password":     "testpass123",
                "confirm_password": "testpass123",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 400
