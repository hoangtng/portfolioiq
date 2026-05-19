"""Tests for Google OAuth login. id_token verification is mocked."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

User = get_user_model()


@pytest.fixture(autouse=True)
def _google_client_id():
    with override_settings(GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com"):
        yield


@pytest.mark.django_db
class TestGoogleLogin:

    def _valid_payload(self, email="newuser@gmail.com"):
        return {
            "email": email,
            "email_verified": True,
            "given_name":     "Test",
            "family_name":    "User",
            "picture":        "https://example.com/avatar.png",
            "sub": "google-uid-12345",
        }

    def test_new_user_created(self, client):
        with patch("apps.users.google.id_token.verify_oauth2_token",
                   return_value=self._valid_payload()):
            resp = client.post(
                "/api/auth/google/",
                {"id_token": "fake-token"},
                content_type="application/json",
            )

        assert resp.status_code == 200
        assert resp.json()["created"] is True
        assert User.objects.filter(email="newuser@gmail.com").exists()

    def test_avatar_url_populated_from_google(self, client):
        with patch("apps.users.google.id_token.verify_oauth2_token",
                   return_value=self._valid_payload()):
            client.post(
                "/api/auth/google/",
                {"id_token": "fake-token"},
                content_type="application/json",
            )
        new_user = User.objects.get(email="newuser@gmail.com")
        assert new_user.avatar_url == "https://example.com/avatar.png"

    def test_existing_user_logs_in(self, client, user):
        payload = self._valid_payload(email="ethan@example.com")
        with patch("apps.users.google.id_token.verify_oauth2_token",
                   return_value=payload):
            resp = client.post(
                "/api/auth/google/",
                {"id_token": "fake-token"},
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp.json()["created"] is False

    def test_invalid_token_rejected(self, client):
        with patch(
            "apps.users.google.id_token.verify_oauth2_token",
            side_effect=ValueError("Token expired"),
        ):
            resp = client.post(
                "/api/auth/google/",
                {"id_token": "expired"},
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_unverified_email_rejected(self, client):
        payload = self._valid_payload()
        payload["email_verified"] = False
        with patch("apps.users.google.id_token.verify_oauth2_token",
                   return_value=payload):
            resp = client.post(
                "/api/auth/google/",
                {"id_token": "fake-token"},
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_new_user_has_unusable_password(self, client):
        with patch("apps.users.google.id_token.verify_oauth2_token",
                   return_value=self._valid_payload()):
            client.post(
                "/api/auth/google/",
                {"id_token": "fake-token"},
                content_type="application/json",
            )
        new_user = User.objects.get(email="newuser@gmail.com")
        assert not new_user.has_usable_password()


@pytest.mark.django_db
class TestGoogleLoginConfig:

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="")
    def test_returns_400_when_not_configured(self, client):
        resp = client.post(
            "/api/auth/google/",
            {"id_token": "anything"},
            content_type="application/json",
        )
        assert resp.status_code == 400
