import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.tenancy import services as tenancy
from apps.tenancy.models import Tenant
from config.api import ApiError
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import ADMIN_HOST, host, login
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/agenda-settings/"
DEFAULTS = {
    "slot_step_min": 15,
    "min_notice_min": 60,
    "max_advance_days": 60,
    "cancel_min_hours": 1,
}


def client_for(tenant, role):
    client = APIClient()
    login(client, UserFactory(tenant=tenant, role=role), host(tenant.slug))
    client.defaults["HTTP_HOST"] = host(tenant.slug)
    return client


# --- Servicio y base de datos ------------------------------------------------------------------


def test_a_new_business_starts_with_the_spec_defaults():
    assert tenancy.agenda_settings(TenantFactory()) == DEFAULTS


def test_update_changes_only_the_given_fields():
    tenant = TenantFactory()
    result = tenancy.update_agenda_settings(tenant, slot_step_min=30)
    tenant.refresh_from_db()
    assert result == {**DEFAULTS, "slot_step_min": 30}
    assert tenant.slot_step_min == 30


@pytest.mark.parametrize(
    "field, value",
    [
        ("slot_step_min", 4),
        ("slot_step_min", 121),
        ("max_advance_days", 0),
        ("max_advance_days", 366),
        ("min_notice_min", 60 * 24 * 7 + 1),
        ("cancel_min_hours", 24 * 7 + 1),
    ],
)
def test_out_of_range_values_are_rejected(field, value):
    tenant = TenantFactory()
    with pytest.raises(ApiError) as error:
        tenancy.update_agenda_settings(tenant, **{field: value})
    assert field in error.value.fields
    tenant.refresh_from_db()
    assert getattr(tenant, field) == DEFAULTS[field]


def test_other_tenant_fields_cannot_be_changed_through_agenda_settings():
    with pytest.raises(ApiError) as error:
        tenancy.update_agenda_settings(TenantFactory(), name="Otro nombre")
    assert "name" in error.value.fields


def test_the_database_also_rejects_out_of_range_values():
    """Un `update()` no pasa por los validadores: la restricción de la base es la última barrera."""
    tenant = TenantFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        Tenant.objects.filter(pk=tenant.pk).update(slot_step_min=1)


# --- API ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["owner", "admin"])
def test_owner_and_admin_can_read_the_settings(role):
    tenant = TenantFactory()
    response = client_for(tenant, role).get(URL)
    assert response.status_code == 200
    assert response.json() == DEFAULTS


@pytest.mark.parametrize("role", ["receptionist", "professional"])
def test_other_roles_cannot_read_the_settings(role):
    tenant = TenantFactory()
    assert client_for(tenant, role).get(URL).status_code == 403


def test_only_the_owner_can_change_the_settings():
    tenant = TenantFactory()

    response = client_for(tenant, "owner").patch(
        URL, {"slot_step_min": 20, "cancel_min_hours": 24}, format="json"
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {**DEFAULTS, "slot_step_min": 20, "cancel_min_hours": 24}
    for role in ("admin", "receptionist", "professional"):
        denied = client_for(tenant, role).patch(URL, {"slot_step_min": 30}, format="json")
        assert denied.status_code == 403
    tenant.refresh_from_db()
    assert tenant.slot_step_min == 20


def test_invalid_values_return_the_standard_error_format():
    tenant = TenantFactory()
    response = client_for(tenant, "owner").patch(URL, {"slot_step_min": 3}, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "slot_step_min" in response.json()["fields"]


def test_each_business_only_sees_and_changes_its_own_settings():
    alfa, beta = TenantFactory(), TenantFactory()
    client_for(alfa, "owner").patch(URL, {"max_advance_days": 90}, format="json")

    alfa.refresh_from_db()
    beta.refresh_from_db()
    assert alfa.max_advance_days == 90
    assert beta.max_advance_days == 60
    assert client_for(beta, "owner").get(URL).json()["max_advance_days"] == 60


def test_anonymous_and_platform_host_get_no_settings():
    tenant = TenantFactory()
    assert APIClient().get(URL, HTTP_HOST=host(tenant.slug)).status_code == 401
    assert APIClient().get(URL, HTTP_HOST=ADMIN_HOST).status_code in (401, 403)
