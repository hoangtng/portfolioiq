"""
Django settings for PortfolioIQ.

All values come from .env via django-environ.
Settings are complete for all phases — later phases only need to add the
app name to INSTALLED_APPS and the URL route to urls.py.
"""

from pathlib import Path
from datetime import timedelta
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

# ─── Core ─────────────────────────────────────────────────────
SECRET_KEY    = env("DJANGO_SECRET_KEY")
DEBUG         = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

SITE_ID = 1

# ─── Installed apps ───────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    "django_celery_results",
    "django_elasticsearch_dsl",
]

LOCAL_APPS = [
    "apps.users",
    "apps.portfolio",
    "apps.journal",
    "apps.ai",
    "apps.analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ───────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF       = "config.urls"
WSGI_APPLICATION   = "config.wsgi.application"
ASGI_APPLICATION   = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES = [
    {
        "BACKEND":  "django.template.backends.django.DjangoTemplates",
        "DIRS":     [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ─── Auth ─────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Database ─────────────────────────────────────────────────
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# ─── Cache (Redis) ────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND":  "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
        "TIMEOUT":  300,
    },
}

# ─── Celery ───────────────────────────────────────────────────
CELERY_BROKER_URL      = env("CELERY_BROKER_URL",     default="redis://redis:6379/1")
CELERY_RESULT_BACKEND  = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_ACCEPT_CONTENT  = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE         = env("DJANGO_TIME_ZONE", default="UTC")
CELERY_BEAT_SCHEDULER   = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_TIME_LIMIT  = 5 * 60   # hard kill at 5 min
CELERY_TASK_SOFT_TIME_LIMIT = 4 * 60   # SIGTERM at 4 min

# ─── Elasticsearch (used from Phase 2 onwards) ───────────────
ELASTICSEARCH_DSL = {
    "default": {
        "hosts": env("ELASTICSEARCH_URL", default="http://elasticsearch:9200"),
    },
}

# ─── Django REST Framework ────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",
    },
}

# ─── simplejwt ────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD":  "id",
    "USER_ID_CLAIM":  "user_id",
    "TOKEN_OBTAIN_SERIALIZER":
        "apps.users.serializers.EmailTokenObtainPairSerializer",
}

# ─── CORS ─────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000"],
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ["authorization", "content-type", "x-requested-with"]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

# ─── Static / media ───────────────────────────────────────────
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL   = "/media/"
MEDIA_ROOT  = BASE_DIR / "media"

# ─── Internationalization ─────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = env("DJANGO_TIME_ZONE", default="UTC")
USE_I18N      = True
USE_TZ        = True

# ─── External API keys ───────────────────────────────────────
GOOGLE_OAUTH_CLIENT_ID     = env("GOOGLE_OAUTH2_KEY",     default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH2_SECRET", default="")
POLYGON_API_KEY            = env("POLYGON_API_KEY",            default="")
ANTHROPIC_API_KEY          = env("ANTHROPIC_API_KEY",          default="")
TELEGRAM_BOT_TOKEN         = env("TELEGRAM_BOT_TOKEN",         default="")

# ─── Logging ──────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{asctime} {levelname:<7} {name}: {message}",
            "style":  "{",
        },
    },
    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django":             {"handlers": ["console"], "level": "INFO"},
        "django.db.backends": {"handlers": ["console"], "level": "WARNING"},
        "apps":               {"handlers": ["console"], "level": "INFO"},
        "celery":             {"handlers": ["console"], "level": "INFO"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
