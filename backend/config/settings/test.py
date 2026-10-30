from .dev import *  # noqa: F403

# App y URLs solo para tests: un modelo de negocio mínimo (TenantOwnedModel) para probar RLS.
INSTALLED_APPS = [*INSTALLED_APPS, "tests.testapp"]  # noqa: F405
ROOT_URLCONF = "tests.urls"
# Hash rápido: los tests crean muchos usuarios y PBKDF2 es lento a propósito.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
