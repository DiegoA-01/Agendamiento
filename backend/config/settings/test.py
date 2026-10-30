from .dev import *  # noqa: F403

# App y URLs solo para tests: un modelo de negocio mínimo (TenantOwnedModel) para probar RLS.
INSTALLED_APPS = [*INSTALLED_APPS, "tests.testapp"]  # noqa: F405
ROOT_URLCONF = "tests.urls"
