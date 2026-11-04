"""`/me/` devuelve los permisos del rol, derivados de la misma matriz que valida la API."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.permissions import MATRIX, can, permissions_for_role
from tests.accounts.factories import SuperadminFactory, UserFactory
from tests.tenancy.factories import TenantFactory

from .helpers import ADMIN_HOST, host

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", [role.value for role in User.Role])
def test_permissions_for_role_agree_with_can(role):
    """Cada acción listada está permitida y cada acción permitida está listada: nada se desfasa."""
    listed = permissions_for_role(role)
    for resource, grants in MATRIX.items():
        actions = set(listed.get(resource, {}).get("actions", []))
        allowed = grants[role].actions if role in grants else frozenset()
        assert actions == set(allowed), (role, resource)
        for action in actions:
            assert can(role, resource, action)


def test_me_tells_a_professional_that_appointments_are_only_their_own():
    tenant = TenantFactory(slug="elfilo")
    client = APIClient()
    client.force_login(UserFactory(tenant=tenant, role="professional"))
    permissions = client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).json()["permissions"]
    assert permissions["appointments"] == {
        "scope": "own",
        "actions": ["complete", "no_show", "view"],
    }
    assert "company" not in permissions
    assert "platform" not in permissions


def test_me_lets_the_owner_edit_the_company_and_see_the_plan():
    tenant = TenantFactory(slug="elfilo")
    client = APIClient()
    client.force_login(UserFactory(tenant=tenant, role="owner"))
    permissions = client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).json()["permissions"]
    assert permissions["company"]["actions"] == ["update", "view"]
    assert permissions["plan_modules"] == {"scope": "all", "actions": ["view"]}


def test_me_gives_the_superadmin_only_platform_permissions(settings):
    settings.REQUIRE_TWO_FACTOR = False
    client = APIClient()
    client.force_login(SuperadminFactory())
    permissions = client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).json()["permissions"]
    assert list(permissions) == ["platform"]
