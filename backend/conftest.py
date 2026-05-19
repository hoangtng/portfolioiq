"""
Shared pytest fixtures. Automatically available in every test file in tests/.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="ethan@example.com",
        password="testpass123",
        first_name="Ethan",
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
    )


@pytest.fixture
def access_token(client, user):
    resp = client.post(
        "/api/auth/token/",
        {"email": "ethan@example.com", "password": "testpass123"},
        content_type="application/json",
    )
    return resp.json()["access"]


@pytest.fixture
def auth_headers(access_token):
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

@pytest.fixture
def access_token(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    return str(RefreshToken.for_user(user).access_token)

