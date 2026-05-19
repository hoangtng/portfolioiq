"""
Custom User model for PortfolioIQ.

Email is unique and is the login field. Changing AUTH_USER_MODEL after
the first migration is painful, so we get this right on day one. Email
auth also enables Google OAuth cleanly (Google returns email, not username).
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """
    Manager that uses email as the unique identifier.

    AbstractUser still requires a username field, so we auto-derive it
    from the email. The user never sees or uses their username.
    """

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email).lower()

        if not extra_fields.get("username"):
            extra_fields["username"] = email

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff",     False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff",     True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    objects = UserManager()
    # Core identity
    email = models.EmailField("email address", unique=True)

    # Profile
    avatar_url = models.URLField(blank=True, default="")
    bio        = models.TextField(blank=True, default="")

    # Integrations
    telegram_chat_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Telegram chat ID for price-alert and AI notifications",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def display_name(self) -> str:
        """Full name when available, falling back to username, then email."""
        return self.get_full_name() or self.username or self.email
