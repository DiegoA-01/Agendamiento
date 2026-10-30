import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(int(default))).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if host.strip()
]
BASE_DOMAIN = os.environ.get("BASE_DOMAIN", "localhost")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "drf_spectacular",
    "apps.tenancy",
    "apps.accounts",
    "apps.company",
    "apps.platform_admin",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.tenancy.middleware.TenantMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.TenantSessionGuardMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "agenda"),
        # Rol sin superusuario: PostgreSQL ignora RLS para superusuarios.
        "USER": os.environ.get("APP_DB_USER", "agenda_app"),
        "PASSWORD": os.environ.get("APP_DB_PASSWORD", "agenda_app"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# i18n: español por defecto, inglés disponible. Fechas siempre UTC en base de datos.
LANGUAGE_CODE = "es"
LANGUAGES = [("es", "Español"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
TIME_ZONE = "UTC"
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Verificación en dos pasos. Encendida por defecto. Se apaga SOLO en desarrollo para probar sin
# autenticador (REQUIRE_TWO_FACTOR=0 en .env); producción no arranca con ella apagada (prod.py).
# REACTIVAR antes de entregar: ver pormejorar.md.
REQUIRE_TWO_FACTOR = env_bool("REQUIRE_TWO_FACTOR", True)

# Cuentas. Sesión por cookie HttpOnly + CSRF (ver docs/adr/0001-autenticacion-por-sesion.md).
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.AccountsBackend"]
# El correo es único por tenant (restricciones condicionales), no globalmente.
SILENCED_SYSTEM_CHECKS = ["auth.E003", "auth.W004"]
# Argon2id primero: las contraseñas nuevas lo usan. PBKDF2 sigue en la lista para verificar hashes
# viejos; Django los convierte a Argon2id solo la próxima vez que esa persona entra.
PASSWORD_HASHERS = [
    "config.hashers.Argon2idHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Agenda <no-reply@localhost>")

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.accounts.authentication.SessionAuth"],
    # Seguro por defecto: toda vista exige sesión salvo que declare otra cosa.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "config.api.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Agenda SaaS API",
    "DESCRIPTION": "API del SaaS de agendamiento para barberías y salones (Fase 1).",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = "UTC"
CELERY_TASK_ACKS_LATE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "config.logging.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
