import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.platform_admin.models import AuditLog
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import ADMIN_HOST, host
from tests.tenancy.factories import PlanFactory, TenantFactory

from .conftest import call

pytestmark = pytest.mark.django_db

TENANT_ID = "00000000-0000-0000-0000-000000000001"
DOMAIN_ID = "00000000-0000-0000-0000-000000000002"
ENDPOINTS = [
    ("get", "/api/v1/tenants/"),
    ("post", "/api/v1/tenants/"),
    ("get", f"/api/v1/tenants/{TENANT_ID}/"),
    ("patch", f"/api/v1/tenants/{TENANT_ID}/"),
    ("delete", f"/api/v1/tenants/{TENANT_ID}/"),
    ("post", f"/api/v1/tenants/{TENANT_ID}/suspend/"),
    ("post", f"/api/v1/tenants/{TENANT_ID}/activate/"),
    ("get", f"/api/v1/tenants/{TENANT_ID}/theme/"),
    ("put", f"/api/v1/tenants/{TENANT_ID}/theme/"),
    ("get", f"/api/v1/tenants/{TENANT_ID}/modules/"),
    ("put", f"/api/v1/tenants/{TENANT_ID}/modules/"),
    ("get", f"/api/v1/tenants/{TENANT_ID}/domains/"),
    ("post", f"/api/v1/tenants/{TENANT_ID}/domains/"),
    ("delete", f"/api/v1/tenants/{TENANT_ID}/domains/{DOMAIN_ID}/"),
    ("post", f"/api/v1/tenants/{TENANT_ID}/domains/{DOMAIN_ID}/verify/"),
    ("get", "/api/v1/plans/"),
    ("post", "/api/v1/plans/"),
    ("get", f"/api/v1/plans/{TENANT_ID}/"),
    ("patch", f"/api/v1/plans/{TENANT_ID}/"),
    ("delete", f"/api/v1/plans/{TENANT_ID}/"),
    ("get", "/api/v1/audit-log/"),
]


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_anonymous_gets_401_on_every_platform_endpoint(method, path):
    response = call(APIClient(), method, path, {})
    assert response.status_code == 401, (method, path)


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_a_business_user_cannot_use_the_platform_api_from_the_admin_host(method, path):
    """Un usuario de un negocio con sesión válida que apunta al host admin queda anónimo."""
    user = UserFactory(tenant=TenantFactory(slug="elfilo"), role="owner")
    client = APIClient()
    client.force_login(user)
    assert call(client, method, path, {}).status_code == 401


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_a_superadmin_session_is_useless_on_a_business_host(api, method, path):
    TenantFactory(slug="elfilo")
    response = call(api, method, path, {}, host=host("elfilo"))
    assert response.status_code == 401, (method, path)


def test_platform_api_is_not_reachable_on_an_unknown_host(api):
    response = call(api, "get", "/api/v1/tenants/", host=f"inventado.{settings.BASE_DOMAIN}")
    assert response.status_code == 404


def test_superadmin_can_reach_every_listing(api):
    for path in ("/api/v1/tenants/", "/api/v1/plans/", "/api/v1/audit-log/"):
        assert call(api, "get", path).status_code == 200


def test_csrf_is_enforced_on_platform_writes(root):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(root)
    response = client.post(
        "/api/v1/plans/",
        {"name": "X", "modules": [], "max_professionals": 1, "max_locations": 1},
        format="json",
        HTTP_HOST=ADMIN_HOST,
    )
    assert response.status_code == 403


# --- Auditoría ---------------------------------------------------------------------------------


def test_audit_log_lists_newest_first_with_actor_and_tenant(api, plan):
    tenant = TenantFactory(plan=plan, name="Barbería Uno")
    call(api, "post", f"/api/v1/tenants/{tenant.pk}/suspend/")
    call(api, "post", f"/api/v1/tenants/{tenant.pk}/activate/")
    rows = call(api, "get", "/api/v1/audit-log/").json()["results"]
    assert [r["action"] for r in rows] == ["tenant.activate", "tenant.suspend"]
    assert rows[0]["actor_email"] == "root@demo.com"
    assert rows[0]["tenant_name"] == "Barbería Uno"
    assert rows[1]["before"] == {"status": "active"} and rows[1]["after"] == {"status": "suspended"}


def test_audit_log_filters_by_tenant_and_action(api, plan):
    uno, dos = TenantFactory(plan=plan), TenantFactory(plan=plan)
    for tenant in (uno, dos):
        call(api, "post", f"/api/v1/tenants/{tenant.pk}/suspend/")
    call(api, "post", f"/api/v1/tenants/{uno.pk}/activate/")

    only_uno = call(api, "get", f"/api/v1/audit-log/?tenant_id={uno.pk}").json()["results"]
    assert {r["tenant_id"] for r in only_uno} == {str(uno.pk)} and len(only_uno) == 2
    only_suspend = call(api, "get", "/api/v1/audit-log/?action=tenant.suspend").json()["results"]
    assert len(only_suspend) == 2


def test_audit_log_rejects_a_malformed_tenant_filter(api):
    response = call(api, "get", "/api/v1/audit-log/?tenant_id=basura")
    assert response.status_code == 400
    assert "tenant_id" in response.json()["fields"]


def test_audit_log_is_paginated_by_cursor(api):
    plan = PlanFactory()
    tenant = TenantFactory(plan=plan)
    for _ in range(30):
        call(api, "post", f"/api/v1/tenants/{tenant.pk}/suspend/")
    first = call(api, "get", "/api/v1/audit-log/?page_size=20").json()
    assert len(first["results"]) == 20 and first["next"]
    second = api.get(first["next"], HTTP_HOST=ADMIN_HOST).json()
    assert len(second["results"]) == 10
    ids = [r["id"] for r in first["results"] + second["results"]]
    assert len(set(ids)) == 30


def test_failed_actions_leave_no_audit_entry(api, plan):
    call(
        api,
        "post",
        "/api/v1/plans/",
        {"name": "X", "modules": ["raro"], "max_professionals": 1, "max_locations": 1},
    )
    call(api, "put", f"/api/v1/tenants/{TenantFactory(plan=plan).pk}/theme/", {"primary": "rojo"})
    assert not AuditLog.objects.exists()
