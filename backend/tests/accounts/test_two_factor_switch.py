"""Interruptor REQUIRE_TWO_FACTOR: apagado solo para probar en desarrollo; producción lo impide."""

import importlib
import logging
import sys

import pytest
from django.apps import apps
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.test import APIClient

from tests.accounts.factories import SuperadminFactory, UserFactory
from tests.tenancy.factories import TenantFactory

from .helpers import ADMIN_HOST, enable_two_factor, host, login

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _reload_base_settings_afterwards():
    """Los tests de producción recargan `base` con variables falsas: se deja como estaba. Al ser
    autouse se desarma después de `monkeypatch`, es decir, con el entorno ya restaurado."""
    yield
    importlib.reload(importlib.import_module("config.settings.base"))


def test_two_factor_is_required_by_default_in_tests():
    assert django_settings.REQUIRE_TWO_FACTOR is True


def test_switched_off_superadmin_logs_in_with_the_password_only(settings):
    settings.REQUIRE_TWO_FACTOR = False
    root = SuperadminFactory()
    client = APIClient()
    response = login(client, root, ADMIN_HOST)
    assert response.status_code == 200
    assert response.json()["is_platform_admin"] is True
    assert client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).status_code == 200


def test_switched_off_ignores_an_already_enabled_second_factor(settings):
    settings.REQUIRE_TWO_FACTOR = False
    root = SuperadminFactory()
    enable_two_factor(root)
    assert login(APIClient(), root, ADMIN_HOST).status_code == 200


def test_switched_off_business_owner_with_two_factor_enters_without_code(settings):
    settings.REQUIRE_TWO_FACTOR = False
    owner = UserFactory(tenant=TenantFactory(slug="elfilo"), role="owner")
    enable_two_factor(owner)
    assert login(APIClient(), owner, host("elfilo")).status_code == 200


def test_switched_on_still_blocks_the_superadmin_without_code():
    root = SuperadminFactory()
    assert login(APIClient(), root, ADMIN_HOST).json()["code"] == "two_factor_setup_required"
    enable_two_factor(root)
    assert login(APIClient(), root, ADMIN_HOST).json()["code"] == "two_factor_required"


def test_wrong_password_is_still_rejected_when_switched_off(settings):
    settings.REQUIRE_TWO_FACTOR = False
    root = SuperadminFactory()
    assert login(APIClient(), root, ADMIN_HOST, password="otra-clave-123").status_code == 401


def test_startup_warns_loudly_when_switched_off(settings, caplog):
    settings.REQUIRE_TWO_FACTOR = False
    with caplog.at_level(logging.WARNING, logger="apps.accounts.apps"):
        apps.get_app_config("accounts").ready()
    assert "DESACTIVADA" in caplog.text


def test_startup_is_silent_when_required(caplog):
    with caplog.at_level(logging.WARNING, logger="apps.accounts.apps"):
        apps.get_app_config("accounts").ready()
    assert "DESACTIVADA" not in caplog.text


def _import_prod(monkeypatch, require_two_factor: str | None):
    monkeypatch.setenv("DJANGO_SECRET_KEY", "clave-de-prueba")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "ejemplo.com")
    if require_two_factor is None:
        monkeypatch.delenv("REQUIRE_TWO_FACTOR", raising=False)
    else:
        monkeypatch.setenv("REQUIRE_TWO_FACTOR", require_two_factor)
    importlib.reload(importlib.import_module("config.settings.base"))
    monkeypatch.delitem(sys.modules, "config.settings.prod", raising=False)
    return importlib.import_module("config.settings.prod")


@pytest.mark.parametrize("value", ["0", "false", "no", "off"])
def test_production_refuses_to_start_with_two_factor_switched_off(monkeypatch, value):
    with pytest.raises(ImproperlyConfigured, match="dos pasos"):
        _import_prod(monkeypatch, value)


def test_production_starts_when_two_factor_is_required_or_unset(monkeypatch):
    for value in (None, "1", "true"):
        prod = _import_prod(monkeypatch, value)
        assert prod.REQUIRE_TWO_FACTOR is True
