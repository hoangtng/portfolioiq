"""Views for the users app."""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ChangePasswordSerializer,
    GoogleLoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Body: { "email": "...", "password": "...", "first_name"?: "...", "last_name"?: "..." }

    Returns the created user. They must call /auth/token/ to get a JWT pair.
    """
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class GoogleLoginView(APIView):
    """
    POST /api/auth/google/
    Body: { "id_token": "<Google ID token>" }
    Returns: { "access": "...", "refresh": "...", "created": true|false }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    GET   /api/auth/me/   return current user
    PATCH /api/auth/me/   update profile (username, first_name, last_name,
                          avatar_url, bio, telegram_chat_id)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Body: {
        "current_password": "...",
        "new_password":     "...",
        "confirm_password": "..."
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed successfully."})
