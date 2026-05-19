"""
Google OAuth helpers.

Frontend gets an ID token from Google's Sign-In SDK and POSTs it to
/api/auth/google/. This module verifies the token and either returns
the existing user or creates a new one.
"""

import logging
from django.contrib.auth import get_user_model
from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)
User   = get_user_model()


class GoogleAuthError(Exception):
    """Raised when a Google ID token is invalid, expired, or unverified."""


def verify_google_id_token(token: str) -> dict:
    """
    Verify a Google ID token against our OAuth client ID.

    Returns the decoded payload: email, email_verified, given_name,
    family_name, picture, sub.

    Raises GoogleAuthError on any failure.
    """
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise GoogleAuthError(
            "Google OAuth is not configured — set GOOGLE_OAUTH_CLIENT_ID in .env"
        )

    try:
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except ValueError as exc:
        raise GoogleAuthError(f"Invalid Google token: {exc}") from exc

    if not payload.get("email"):
        raise GoogleAuthError("Google token has no email")
    if not payload.get("email_verified"):
        raise GoogleAuthError("Google email is not verified")

    return payload


def get_or_create_google_user(payload: dict) -> tuple[User, bool]:
    """
    Find or create a user from Google data.

    Returns (user, created). Brand-new accounts get an unusable password —
    they can only ever log in via Google.
    """
    email      = payload["email"].lower()
    first_name = payload.get("given_name",  "")
    last_name  = payload.get("family_name", "")
    picture    = payload.get("picture",     "")

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username":   email,
            "first_name": first_name,
            "last_name":  last_name,
            "avatar_url": picture,
        },
    )

    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
        logger.info("Created new user from Google: %s", email)
    else:
        # Backfill any missing fields on existing accounts
        updated = []
        if not user.first_name and first_name:
            user.first_name = first_name
            updated.append("first_name")
        if not user.last_name and last_name:
            user.last_name = last_name
            updated.append("last_name")
        if not user.avatar_url and picture:
            user.avatar_url = picture
            updated.append("avatar_url")
        if updated:
            user.save(update_fields=updated)

    return user, created
