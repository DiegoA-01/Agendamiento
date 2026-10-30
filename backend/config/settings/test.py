from .dev import *  # noqa: F403

# App y URLs solo para tests: un modelo de negocio mínimo (TenantOwnedModel) para probar RLS.
INSTALLED_APPS = [*INSTALLED_APPS, "tests.testapp"]  # noqa: F405
ROOT_URLCONF = "tests.urls"
# Los tests siempre corren con el 2FA exigido, aunque el .env local lo tenga apagado.
REQUIRE_TWO_FACTOR = True
# Hash rápido: los tests crean muchos usuarios y PBKDF2 es lento a propósito.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
