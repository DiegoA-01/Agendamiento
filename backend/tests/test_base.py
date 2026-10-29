import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client


@pytest.mark.django_db
def test_healthz_ok() -> None:
    response = Client().get("/healthz/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


def test_healthz_degraded_when_redis_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import health

    monkeypatch.setattr(health, "_check_db", lambda: True)
    monkeypatch.setattr(health, "_check_redis", lambda: False)
    response = Client().get("/healthz/")
    assert response.status_code == 503
    assert response.json()["checks"]["redis"] == "fail"


def test_openapi_schema_is_served() -> None:
    response = Client().get("/api/schema/")
    assert response.status_code == 200
    assert b"openapi" in response.content


def test_i18n_defaults() -> None:
    assert settings.LANGUAGE_CODE == "es"
    assert [code for code, _ in settings.LANGUAGES] == ["es", "en"]
    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "UTC"


@pytest.mark.parametrize("accept,expected", [("en", "en"), ("es", "es"), ("fr", "es")])
def test_locale_middleware_negotiates_language(accept: str, expected: str) -> None:
    response = Client().get("/healthz/", headers={"Accept-Language": accept})
    assert response.headers["Content-Language"] == expected


def test_prod_settings_require_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    monkeypatch.delenv("DJANGO_ALLOWED_HOSTS", raising=False)
    import config.settings.base as base
    import config.settings.prod as prod

    importlib.reload(base)
    with pytest.raises(ImproperlyConfigured):
        importlib.reload(prod)
