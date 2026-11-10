from .dev import *  # noqa: F403

# App y URLs solo para tests: un modelo de negocio mínimo (TenantOwnedModel) para probar RLS.
INSTALLED_APPS = [*INSTALLED_APPS, "tests.testapp"]  # noqa: F405
ROOT_URLCONF = "tests.urls"
# Los tests siempre corren con el 2FA exigido, aunque el .env local lo tenga apagado.
REQUIRE_TWO_FACTOR = True
# Hash rápido: los tests crean muchos usuarios y PBKDF2 es lento a propósito.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# Los límites de intentos de login cuentan en Redis y duran 15 minutos: con valores reales, la
# suite completa (muchos logins fallidos desde la misma IP) se bloquearía sola. Las pruebas del
# límite los bajan con el fixture `settings` y usan IP y correo únicos.
AUTH_LIMIT_PER_IP = 10_000
AUTH_LIMIT_PER_EMAIL = 10_000
PASSWORD_RESET_LIMIT_PER_IP = 10_000
PASSWORD_RESET_LIMIT_PER_EMAIL = 10_000
# Celery en el mismo proceso y sin broker: ninguna prueba encola tareas en el Redis real (las
# pruebas con commits reales, como la de concurrencia, disparan `on_commit`).
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
