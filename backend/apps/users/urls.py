"""
Auth routes mounted at /api/auth/

  POST   /api/auth/register/           create account
  POST   /api/auth/token/              login with email + password
  POST   /api/auth/token/refresh/      rotate access token
  POST   /api/auth/token/verify/       validate a token
  POST   /api/auth/logout/             blacklist a refresh token
  POST   /api/auth/google/             login with Google ID token
  POST   /api/auth/change-password/    change current user's password
  GET    /api/auth/me/                 get current user
  PATCH  /api/auth/me/                 update profile
"""

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    ChangePasswordView,
    GoogleLoginView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("register/",        RegisterView.as_view(),         name="auth_register"),
    path("token/",           TokenObtainPairView.as_view(),  name="token_obtain_pair"),
    path("token/refresh/",   TokenRefreshView.as_view(),     name="token_refresh"),
    path("token/verify/",    TokenVerifyView.as_view(),      name="token_verify"),
    path("logout/",          TokenBlacklistView.as_view(),   name="auth_logout"),
    path("google/",          GoogleLoginView.as_view(),      name="auth_google"),
    path("change-password/", ChangePasswordView.as_view(),   name="auth_change_password"),
    path("me/",              MeView.as_view(),               name="auth_me"),
]
