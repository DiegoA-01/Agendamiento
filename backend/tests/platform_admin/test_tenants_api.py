import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.company.models import Company
from apps.platform_admin.models import AuditLog
from apps.tenancy import services as tenancy
from apps.tenancy.models import Domain, Tenant
from tests.accounts.helpers import host, login
from tests.factories import PASSWORD, PlanFactory, TenantFactory

from .conftest import call, new_tenant_payload

pytestmark = pytest.mark.django_db


def create(api, plan, **overrides):
    return call(api, "post", "/api/v1/tenants/", new_tenant_payload(plan, **overrides))


# --- Alta --------------------------------------------------------------------------------------


def test_create_tenant_builds_everything_the_acceptance_criterion_needs(api, plan):
    response = create(api, plan)
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["tenant"]["slug"] == "elfilo"
    assert body["tenant"]["status"] == "active"
    assert body["tenant"]["modules"] == ["booking", "commissions"]
    assert body["tenant"]["theme"]["text"] == "#111827"
    assert body["owner"] == {"email": "dueno@elfilo.com", "full_name": "Diego Dueño"}
    assert len(body["temporary_password"]) >= 12

    tenant = Tenant.objects.get(slug="elfilo")
    subdomain = Domain.objects.get(tenant=tenant)
    assert (subdomain.host, subdomain.verified, subdomain.kind) == (
        f"elfilo.{settings.BASE_DOMAIN}",
        True,
        "subdomain",
    )
    assert tenancy.get_current_tenant() is None
    with tenancy.tenant_context(tenant):
        assert Company.objects.get().trade_name == "Barbería El Filo"


def test_owner_can_log_in_on_the_new_subdomain_and_must_change_the_temporary_password(api, plan):
    password = create(api, plan).json()["temporary_password"]
    owner = User.objects.get(email="dueno@elfilo.com")
    assert owner.role == "owner" and owner.must_change_password is True

    owner_client = APIClient()
    response = login(owner_client, owner, host("elfilo"), password=password)
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True
    assert response.json()["modules"] == ["booking", "commissions"]

    changed = owner_client.post(
        "/api/v1/auth/password-change/",
        {"current_password": password, "new_password": "Mi-Clave-Definitiva-2026!"},
        format="json",
        HTTP_HOST=host("elfilo"),
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert login(APIClient(), owner, host("elfilo"), password=password).status_code == 401


def test_temporary_password_is_never_written_to_the_audit_log(api, plan):
    password = create(api, plan).json()["temporary_password"]
    entry = AuditLog.objects.get(action="tenant.create")
    assert password not in str(entry.after) and password not in str(entry.before)
    assert entry.actor.email == "root@demo.com"
    assert entry.after["owner_email"] == "dueno@elfilo.com"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"slug": "admin"}, "slug"),
        ({"slug": "Con Espacios"}, "slug"),
        ({"timezone": "Marte/Olimpo"}, "timezone"),
        ({"owner_email": "no-es-correo"}, "owner_email"),
        ({"plan_id": "00000000-0000-0000-0000-000000000000"}, "plan_id"),
        ({"vertical": "panaderia"}, "vertical"),
    ],
)
def test_create_tenant_rejects_bad_data_without_leaving_anything_behind(
    api, plan, overrides, field
):
    response = create(api, plan, **overrides)
    assert response.status_code == 400
    assert field in response.json()["fields"]
    assert not Tenant.objects.exists() and not User.objects.filter(role="owner").exists()
    assert not AuditLog.objects.exists()


def test_duplicate_slug_is_rejected(api, plan):
    assert create(api, plan).status_code == 201
    response = create(api, plan, owner_email="otro@x.com")
    assert response.status_code == 400
    assert "slug" in response.json()["fields"]


def test_creation_is_all_or_nothing(api, plan, monkeypatch):
    """Si falla un paso (aquí, la empresa), no queda un negocio a medias."""
    from apps.company import services as company

    def boom(*args, **kwargs):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(company, "create_company", boom)
    api.raise_request_exception = False
    response = create(api, plan)
    assert response.status_code == 500
    assert not Tenant.objects.exists()
    assert not Domain.objects.exists()
    assert not User.objects.filter(role="owner").exists()
    assert not AuditLog.objects.exists()


# --- Lectura -----------------------------------------------------------------------------------


def test_list_uses_cursor_pagination_and_filters(api, plan):
    for number in range(30):
        TenantFactory(name=f"Negocio {number:02d}", slug=f"negocio-{number:02d}", plan=plan)
    TenantFactory(name="Salón Aura", slug="aura", plan=plan, with_domain=False)
    Tenant.objects.filter(slug="negocio-00").update(status="suspended")

    first = call(api, "get", "/api/v1/tenants/").json()
    assert len(first["results"]) == 25 and first["next"]
    second = api.get(first["next"], HTTP_HOST=f"admin.{settings.BASE_DOMAIN}").json()
    assert len(second["results"]) == 6 and second["next"] is None
    seen = {t["slug"] for t in first["results"]} | {t["slug"] for t in second["results"]}
    assert len(seen) == 31

    assert [t["slug"] for t in call(api, "get", "/api/v1/tenants/?q=aura").json()["results"]] == [
        "aura"
    ]
    suspended = call(api, "get", "/api/v1/tenants/?status=suspended").json()["results"]
    assert [t["slug"] for t in suspended] == ["negocio-00"]


def test_detail_shows_modules_and_unknown_id_is_404(api, plan):
    tenant = TenantFactory(plan=plan)
    body = call(api, "get", f"/api/v1/tenants/{tenant.pk}/").json()
    assert body["modules"] == ["booking", "commissions"]
    assert body["plan"] == {"id": str(plan.pk), "name": "Profesional"}

    missing = call(api, "get", "/api/v1/tenants/00000000-0000-0000-0000-000000000000/")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"


# --- Edición, suspensión y borrado -------------------------------------------------------------


def test_patch_updates_data_but_never_the_slug(api, plan):
    tenant = TenantFactory(slug="elfilo", plan=plan)
    response = call(
        api,
        "patch",
        f"/api/v1/tenants/{tenant.pk}/",
        {"name": "El Filo Premium", "vertical": "salon", "slug": "otro"},
    )
    assert response.status_code == 200
    tenant.refresh_from_db()
    assert (tenant.name, tenant.vertical, tenant.slug) == ("El Filo Premium", "salon", "elfilo")
    entry = AuditLog.objects.get(action="tenant.update")
    assert entry.before["name"] != entry.after["name"]


def test_changing_the_plan_resets_the_modules_to_the_new_plan(api, plan):
    tenant = TenantFactory(plan=plan)
    call(api, "put", f"/api/v1/tenants/{tenant.pk}/modules/", {"modules": {"reports": True}})
    assert "reports" in tenancy.enabled_module_keys(tenant)

    basic = PlanFactory(name="Inicial", modules=["booking"])
    response = call(api, "patch", f"/api/v1/tenants/{tenant.pk}/", {"plan_id": str(basic.pk)})
    assert response.status_code == 200
    assert response.json()["modules"] == ["booking"]


def test_suspend_blocks_the_business_host_and_activate_restores_it(api, plan):
    tenant = TenantFactory(slug="elfilo", plan=plan)
    public = APIClient()
    assert public.get("/api/v1/auth/csrf/", HTTP_HOST=host("elfilo")).status_code == 204

    assert (
        call(api, "post", f"/api/v1/tenants/{tenant.pk}/suspend/").json()["status"] == "suspended"
    )
    blocked = public.get("/api/v1/auth/csrf/", HTTP_HOST=host("elfilo"))
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "tenant_suspended"
    assert public.get("/healthz/", HTTP_HOST=host("elfilo")).status_code == 200

    assert call(api, "post", f"/api/v1/tenants/{tenant.pk}/activate/").json()["status"] == "active"
    assert public.get("/api/v1/auth/csrf/", HTTP_HOST=host("elfilo")).status_code == 204
    assert [e.action for e in AuditLog.objects.order_by("created_at")] == [
        "tenant.suspend",
        "tenant.activate",
    ]


def test_delete_is_logical_and_the_host_stops_resolving(api, plan):
    tenant = TenantFactory(slug="elfilo", plan=plan)
    assert call(api, "delete", f"/api/v1/tenants/{tenant.pk}/").status_code == 204
    assert APIClient().get("/api/v1/auth/csrf/", HTTP_HOST=host("elfilo")).status_code == 404
    assert call(api, "get", f"/api/v1/tenants/{tenant.pk}/").status_code == 404
    assert Tenant.objects.filter(pk=tenant.pk, deleted_at__isnull=False).exists()
    assert not any(
        t["id"] == str(tenant.pk) for t in call(api, "get", "/api/v1/tenants/").json()["results"]
    )


def test_same_owner_email_in_another_tenant_does_not_clash(api, plan):
    """El correo es único por negocio, no global."""
    other = TenantFactory(slug="aura", plan=plan)
    User.objects.create_user(
        "dueno@elfilo.com", PASSWORD, role="owner", tenant=other, full_name="X"
    )
    assert create(api, plan).status_code == 201
    assert User.objects.filter(email="dueno@elfilo.com").count() == 2
