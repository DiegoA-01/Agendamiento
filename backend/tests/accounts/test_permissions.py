"""Matriz de permisos de la spec §5. La tabla EXPECTED se escribió a mano desde el texto de la spec,
sin usar el código que prueba: así el test compara el código contra la spec, no contra sí mismo."""

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts import permissions as perms
from apps.accounts.models import User
from tests.accounts.factories import SuperadminFactory, UserFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db

CRUD = {"view", "create", "update", "delete"}
APPOINTMENT_ALL = CRUD | {"confirm", "start", "complete", "cancel", "no_show", "reschedule"}

# Spec §5, fila por fila.
EXPECTED = {
    "owner": {
        "company": {"view", "update"},
        "staff_services": CRUD,
        "schedules": CRUD,
        "appointments": APPOINTMENT_ALL,
        "commissions": {"view"},
        "plan_modules": {"view"},
    },
    "admin": {
        "company": {"view"},
        "staff_services": CRUD,
        "schedules": CRUD,
        "appointments": APPOINTMENT_ALL,
        "commissions": {"view"},
    },
    "receptionist": {
        "staff_services": {"view"},
        "schedules": CRUD,
        "appointments": APPOINTMENT_ALL,
    },
    "professional": {
        "staff_services": {"view"},
        "schedules": CRUD,
        "appointments": {"view", "complete", "no_show"},
        "commissions": {"view"},
    },
    "superadmin": {"platform": CRUD},
}
# Solo el profesional tiene alcance limitado a lo propio.
EXPECTED_OWN = {
    ("professional", "staff_services"),
    ("professional", "schedules"),
    ("professional", "appointments"),
    ("professional", "commissions"),
}

RESOURCES = [
    perms.COMPANY,
    perms.STAFF_SERVICES,
    perms.SCHEDULES,
    perms.APPOINTMENTS,
    perms.COMMISSIONS,
    perms.PLAN_MODULES,
    perms.PLATFORM,
]
ALL_ACTIONS = sorted(APPOINTMENT_ALL)
ROLES = [role.value for role in User.Role]


def client_for(role: str) -> tuple[APIClient, str]:
    """Cliente con sesión iniciada para un usuario de ese rol, y el host donde corresponde."""
    if role == "superadmin":
        user, host = SuperadminFactory(), f"admin.{settings.BASE_DOMAIN}"
    else:
        tenant = TenantFactory(slug="elfilo")
        user, host = UserFactory(tenant=tenant, role=role), f"elfilo.{settings.BASE_DOMAIN}"
    client = APIClient()
    client.force_login(user)
    return client, host


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("role", ROLES)
def test_permission_matrix_matches_spec_through_the_api(role, resource):
    client, host = client_for(role)
    allowed = EXPECTED[role].get(resource, set())
    for action in ALL_ACTIONS:
        response = client.get(f"/test/perm/{resource}/{action}/", HTTP_HOST=host)
        expected_status = 200 if action in allowed else 403
        assert response.status_code == expected_status, f"{role} {resource}.{action}"


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("role", ROLES)
def test_can_and_scope_match_spec(role, resource):
    allowed = EXPECTED[role].get(resource, set())
    for action in ALL_ACTIONS:
        assert perms.can(role, resource, action) is (action in allowed)
        scope = perms.scope_for(role, resource, action)
        if action not in allowed:
            assert scope is None
        else:
            assert scope == (perms.OWN if (role, resource) in EXPECTED_OWN else perms.ALL)


def test_anonymous_gets_401_not_403():
    response = APIClient().get(
        "/test/perm/appointments/view/", HTTP_HOST=f"admin.{settings.BASE_DOMAIN}"
    )
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_unknown_resource_or_action_is_denied():
    client, host = client_for("owner")
    assert client.get("/test/perm/inventado/view/", HTTP_HOST=host).status_code == 403
    assert client.get("/test/perm/company/inventada/", HTTP_HOST=host).status_code == 403


def test_tenant_roles_never_reach_platform_resources():
    for role in ("owner", "admin", "receptionist", "professional"):
        for action in ALL_ACTIONS:
            assert perms.can(role, perms.PLATFORM, action) is False


def test_superadmin_has_no_access_to_tenant_data():
    """El Super Admin no ve datos de clientes (spec: solo con suplantación auditada, M10)."""
    for resource in RESOURCES:
        if resource == perms.PLATFORM:
            continue
        for action in ALL_ACTIONS:
            assert perms.can("superadmin", resource, action) is False
