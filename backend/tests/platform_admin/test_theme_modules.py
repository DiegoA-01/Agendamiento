import pytest

from apps.platform_admin.models import AuditLog
from apps.tenancy import services as tenancy
from apps.tenancy.constants import LANGUAGES, MODULE_KEYS, VERTICALS
from apps.tenancy.models import Tenant
from apps.tenancy.theme import DEFAULT_THEME, MIN_TEXT_CONTRAST, contrast_ratio
from tests.tenancy.factories import TenantFactory

from .conftest import call

pytestmark = pytest.mark.django_db

GOOD_THEME = {
    "primary": "#0F766E",
    "secondary": "#B45309",
    "background": "#FFFFFF",
    "surface": "#F0FDFA",
    "text": "#0F172A",
}


# --- Contraste (función pura) ------------------------------------------------------------------


def test_contrast_ratio_matches_wcag_reference_values():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast_ratio("#ffffff", "#ffffff") == pytest.approx(1.0)
    # Gris #767676 sobre blanco es el caso límite clásico de WCAG AA: 4.54:1.
    assert contrast_ratio("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)
    assert contrast_ratio("#ffffff", "#000000") == contrast_ratio("#000000", "#ffffff")


def test_default_theme_is_accessible():
    assert contrast_ratio(DEFAULT_THEME["text"], DEFAULT_THEME["background"]) >= MIN_TEXT_CONTRAST
    assert contrast_ratio(DEFAULT_THEME["text"], DEFAULT_THEME["surface"]) >= MIN_TEXT_CONTRAST


# --- API del tema ------------------------------------------------------------------------------


def test_valid_theme_is_saved_normalized_and_audited(api):
    tenant = TenantFactory()
    response = call(api, "put", f"/api/v1/tenants/{tenant.pk}/theme/", GOOD_THEME)
    assert response.status_code == 200
    assert response.json()["primary"] == "#0f766e"  # minúsculas
    tenant.refresh_from_db()
    assert tenant.theme["text"] == "#0f172a"
    assert call(api, "get", f"/api/v1/tenants/{tenant.pk}/theme/").json() == tenant.theme
    assert AuditLog.objects.filter(action="tenant.theme", tenant=tenant).count() == 1


def test_low_contrast_theme_is_rejected_and_nothing_changes(api):
    tenant = TenantFactory(theme=dict(DEFAULT_THEME))
    bad = {**GOOD_THEME, "text": "#CCCCCC"}  # gris claro sobre blanco: ~1.6:1
    response = call(api, "put", f"/api/v1/tenants/{tenant.pk}/theme/", bad)
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "low_contrast"
    assert any("4.5:1" in message for message in body["fields"]["text"])
    tenant.refresh_from_db()
    assert tenant.theme == DEFAULT_THEME
    assert not AuditLog.objects.filter(action="tenant.theme").exists()


def test_contrast_is_checked_against_surface_too(api):
    tenant = TenantFactory()
    bad = {**GOOD_THEME, "text": "#767676", "surface": "#6b7280"}
    response = call(api, "put", f"/api/v1/tenants/{tenant.pk}/theme/", bad)
    assert response.status_code == 400
    assert any("la superficie" in message for message in response.json()["fields"]["text"])


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"primary": "rojo"}, "primary"),
        ({"primary": "#fff"}, "primary"),
        ({"surface": 123}, "surface"),
        ({"fondo": "#ffffff"}, "fondo"),
    ],
)
def test_malformed_themes_are_rejected(api, change, field):
    tenant = TenantFactory()
    response = call(api, "put", f"/api/v1/tenants/{tenant.pk}/theme/", {**GOOD_THEME, **change})
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_theme"
    assert field in response.json()["fields"]


def test_missing_colors_are_rejected(api):
    tenant = TenantFactory()
    response = call(api, "put", f"/api/v1/tenants/{tenant.pk}/theme/", {"primary": "#112233"})
    assert response.status_code == 400
    assert set(response.json()["fields"]) == {"secondary", "background", "surface", "text"}


def test_theme_reaches_the_business_through_me(api):
    from rest_framework.test import APIClient

    from tests.accounts.factories import UserFactory
    from tests.accounts.helpers import host, login

    tenant = TenantFactory(slug="elfilo")
    call(api, "put", f"/api/v1/tenants/{tenant.pk}/theme/", GOOD_THEME)
    user = UserFactory(tenant=tenant)
    client = APIClient()
    login(client, user, host("elfilo"))
    me = client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).json()
    assert me["theme"]["primary"] == "#0f766e"


# --- Módulos -----------------------------------------------------------------------------------


def test_modules_show_available_and_enabled(api, plan):
    tenant = TenantFactory(plan=plan)
    body = call(api, "get", f"/api/v1/tenants/{tenant.pk}/modules/").json()
    assert body["available"] == list(MODULE_KEYS)
    assert body["enabled"] == ["booking", "commissions"]


def test_modules_can_be_toggled_individually(api, plan):
    tenant = TenantFactory(plan=plan)
    response = call(
        api,
        "put",
        f"/api/v1/tenants/{tenant.pk}/modules/",
        {"modules": {"reports": True, "commissions": False}},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] == ["booking", "reports"]
    assert tenancy.is_module_enabled(tenant, "reports") is True
    assert tenancy.is_module_enabled(tenant, "commissions") is False
    entry = AuditLog.objects.get(action="tenant.modules")
    assert entry.before == ["booking", "commissions"] and entry.after == ["booking", "reports"]


@pytest.mark.parametrize(
    "payload", [{"modules": {"teletransporte": True}}, {}, {"modules": {"booking": "tal vez"}}]
)
def test_invalid_module_requests_are_rejected(api, payload):
    tenant = TenantFactory()
    response = call(api, "put", f"/api/v1/tenants/{tenant.pk}/modules/", payload)
    assert response.status_code == 400


def test_disabling_a_module_blocks_the_endpoint_that_requires_it(api, plan):
    from rest_framework.test import APIClient

    from tests.accounts.helpers import host

    tenant = TenantFactory(slug="elfilo", plan=plan)
    client = APIClient()
    assert client.get("/test/booking-only/", HTTP_HOST=host("elfilo")).status_code == 200
    call(api, "put", f"/api/v1/tenants/{tenant.pk}/modules/", {"modules": {"booking": False}})
    blocked = client.get("/test/booking-only/", HTTP_HOST=host("elfilo"))
    assert blocked.status_code == 403 and blocked.json()["code"] == "module_disabled"


def test_api_choices_match_the_model_choices():
    assert set(VERTICALS) == set(Tenant.Vertical.values)
    assert set(LANGUAGES) == set(Tenant.Language.values)
