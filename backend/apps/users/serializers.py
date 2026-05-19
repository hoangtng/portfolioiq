"""
Serializers for the users app.

Five serializers, one file:
  RegisterSerializer              POST /api/auth/register/
  EmailTokenObtainPairSerializer  POST /api/auth/token/
  GoogleLoginSerializer           POST /api/auth/google/
  UserSerializer                  GET / PATCH /api/auth/me/
  ChangePasswordSerializer        POST /api/auth/change-password/
"""

from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .google import (
    GoogleAuthError,
    get_or_create_google_user,
    verify_google_id_token,
)

User = get_user_model()


# ─── Register ─────────────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    """Create a new account with email + password. Username defaults to email."""
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    class Meta:
        model  = User
        fields = ("id", "email", "username", "password",
                  "first_name", "last_name")
        extra_kwargs = {
            "username":   {"required": False},
            "first_name": {"required": False},
            "last_name":  {"required": False},
        }

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        validated_data.setdefault("username", validated_data["email"].split("@")[0])
        return User.objects.create_user(**validated_data)


# ─── Login with email ─────────────────────────────────────────

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    simplejwt token serializer that accepts email + password.
    Wired up via SIMPLE_JWT['TOKEN_OBTAIN_SERIALIZER'] in settings.py.
    """
    username_field = "email"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)
        self.fields["email"] = serializers.EmailField()

    def validate(self, attrs):
        email    = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"email": "No account with that email exists."}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {"password": "Incorrect password."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"email": "This account has been disabled."}
            )

        refresh = RefreshToken.for_user(user)
        return {
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
        }


# ─── Login with Google ────────────────────────────────────────

class GoogleLoginSerializer(serializers.Serializer):
    """Verify a Google ID token, find or create user, return JWT pair."""
    id_token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            payload = verify_google_id_token(attrs["id_token"])
        except GoogleAuthError as exc:
            raise serializers.ValidationError({"id_token": str(exc)})

        user, created = get_or_create_google_user(payload)

        if not user.is_active:
            raise serializers.ValidationError(
                {"id_token": "This account has been disabled."}
            )

        refresh = RefreshToken.for_user(user)
        return {
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
            "created": created,
        }


# ─── User profile ─────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """
    Profile serializer used by GET/PATCH /auth/me/.
    Email and id are read-only.
    """
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = ("id", "email", "username",
                  "first_name", "last_name", "display_name",
                  "avatar_url", "bio", "telegram_chat_id",
                  "created_at")
        read_only_fields = ("id", "email", "display_name", "created_at")


# ─── Change password ──────────────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    """
    Authenticated user changes their own password.

    Requires the current password — without this, a stolen access token
    could permanently take over the account.
    """
    current_password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, required=True, min_length=8, max_length=128,
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(" Current password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        """Run Django's AUTH_PASSWORD_VALIDATORS against the new password."""
        user = self.context["request"].user
        try:
            password_validation.validate_password(value, user=user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"Confirm password": " Passwords do not match."}
            )
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError(
                {"new_password": " New password must be different from the current one."}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
