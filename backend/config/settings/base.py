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
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "apps.tenancy",
    "apps.accounts",
    "apps.company",
    "apps.platform_admin",
    "apps.media",
    "apps.catalog",
    "apps.scheduling",
    "apps.booking",
    "apps.commissions",
    "apps.notifications",
    "apps.reports",
]

MIDDLEWARE = [
    "config.request_id.RequestIdMiddleware",
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
# Archivos subidos (imágenes ya convertidas a WebP por la app `media`).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"
MEDIA_MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Verificación en dos pasos. Encendida por defecto. Se apaga SOLO en desarrollo para probar sin
# autenticador (REQUIRE_TWO_FACTOR=0 en .env); producción no arranca con ella apagada (prod.py).
# REACTIVAR antes de entregar: ver pormejorar.md.
REQUIRE_TWO_FACTOR = env_bool("REQUIRE_TWO_FACTOR", True)

# Reserva pública (M6, spec §9). Límites por hora contra reservas basura.
PUBLIC_BOOKING_LIMIT_PER_IP = int(os.environ.get("PUBLIC_BOOKING_LIMIT_PER_IP", "10"))
PUBLIC_BOOKING_LIMIT_PER_PHONE = int(os.environ.get("PUBLIC_BOOKING_LIMIT_PER_PHONE", "5"))
# Proxies propios delante de Django (Caddy = 1). La IP del cliente es la que el último de ellos
# agregó a X-Forwarded-For; con 0 se usa REMOTE_ADDR. Nunca más alto que los proxies reales: un
# cliente podría falsear la cabecera para saltarse el límite.
TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "1"))

# Límite de intentos (M10): fallos de login por IP y por correo en la ventana, y solicitudes de
# recuperación de contraseña. Ver apps/accounts/throttle.py.
AUTH_LIMIT_WINDOW = int(os.environ.get("AUTH_LIMIT_WINDOW", "900"))  # 15 minutos
AUTH_LIMIT_PER_IP = int(os.environ.get("AUTH_LIMIT_PER_IP", "20"))
AUTH_LIMIT_PER_EMAIL = int(os.environ.get("AUTH_LIMIT_PER_EMAIL", "10"))
PASSWORD_RESET_LIMIT_PER_IP = int(os.environ.get("PASSWORD_RESET_LIMIT_PER_IP", "10"))
PASSWORD_RESET_LIMIT_PER_EMAIL = int(os.environ.get("PASSWORD_RESET_LIMIT_PER_EMAIL", "3"))
# Captcha opcional (Turnstile, hCaptcha o reCAPTCHA: todos validan con un POST secret+response).
PUBLIC_BOOKING_CAPTCHA = env_bool("PUBLIC_BOOKING_CAPTCHA", False)
CAPTCHA_VERIFY_URL = os.environ.get(
    "CAPTCHA_VERIFY_URL", "https://challenges.cloudflare.com/turnstile/v0/siteverify"
)
CAPTCHA_SECRET = os.environ.get("CAPTCHA_SECRET", "")

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
    "ENUM_NAME_OVERRIDES": {
        # Estado de un día del calendario de reserva (R7); choca con `status` de la cita.
        "CalendarDayStatusEnum": ["available", "full", "closed", "unavailable"],
        # El estado de la cita conserva su nombre de siempre.
        "StatusEnum": "apps.booking.models.Appointment.Status",
    },
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
