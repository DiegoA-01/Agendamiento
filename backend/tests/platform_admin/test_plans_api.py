import pytest

from apps.platform_admin.models import AuditLog
from apps.tenancy import services as tenancy
from apps.tenancy.models import Plan
from tests.factories import PlanFactory, TenantFactory

from .conftest import call

pytestmark = pytest.mark.django_db

PAYLOAD = {
    "name": "Negocio",
    "modules": ["booking", "reports"],
    "max_professionals": 10,
    "max_locations": 3,
}


def test_create_and_list_plans(api):
    response = call(api, "post", "/api/v1/plans/", PAYLOAD)
    assert response.status_code == 201
    assert response.json()["modules"] == ["booking", "reports"]
    call(api, "post", "/api/v1/plans/", {**PAYLOAD, "name": "Inicial"})
    names = [p["name"] for p in call(api, "get", "/api/v1/plans/").json()]
    assert names == ["Inicial", "Negocio"]  # ordenados por nombre
    assert AuditLog.objects.filter(action="plan.create").count() == 2


@pytest.mark.parametrize(
    "bad",
    [
        {"modules": ["teletransporte"]},
        {"max_professionals": 0},
        {"max_locations": -1},
        {"name": ""},
    ],
)
def test_invalid_plans_are_rejected(api, bad):
    assert call(api, "post", "/api/v1/plans/", {**PAYLOAD, **bad}).status_code == 400


def test_duplicate_plan_name_is_rejected(api):
    call(api, "post", "/api/v1/plans/", PAYLOAD)
    response = call(api, "post", "/api/v1/plans/", PAYLOAD)
    assert response.status_code == 400
    assert "name" in response.json()["fields"]


def test_patch_changes_only_the_given_fields(api):
    plan = PlanFactory(name="Inicial", modules=["booking"], max_professionals=2)
    response = call(api, "patch", f"/api/v1/plans/{plan.pk}/", {"max_professionals": 5})
    assert response.status_code == 200
    plan.refresh_from_db()
    assert (plan.max_professionals, plan.modules, plan.name) == (5, ["booking"], "Inicial")


def test_editing_a_plan_does_not_touch_existing_tenants_by_default(api):
    plan = PlanFactory(modules=["booking"])
    tenant = TenantFactory(plan=plan)
    call(api, "patch", f"/api/v1/plans/{plan.pk}/", {"modules": ["booking", "reports"]})
    assert tenancy.enabled_module_keys(tenant) == {"booking"}


def test_apply_to_tenants_pushes_the_new_modules_and_overwrites_manual_changes(api):
    plan = PlanFactory(modules=["booking"])
    tenant = TenantFactory(plan=plan)
    other_plan_tenant = TenantFactory(plan=PlanFactory(name="Otro", modules=["booking"]))
    tenancy.set_modules(tenant, {"commissions": True})

    call(
        api,
        "patch",
        f"/api/v1/plans/{plan.pk}/",
        {"modules": ["booking", "reports"], "apply_to_tenants": True},
    )
    assert tenancy.enabled_module_keys(tenant) == {"booking", "reports"}
    assert tenancy.enabled_module_keys(other_plan_tenant) == {"booking"}
    assert AuditLog.objects.get(action="plan.update").after["apply_to_tenants"] is True


def test_a_plan_in_use_cannot_be_deleted(api):
    plan = PlanFactory()
    TenantFactory(plan=plan)
    response = call(api, "delete", f"/api/v1/plans/{plan.pk}/")
    assert response.status_code == 409
    assert response.json()["code"] == "plan_in_use"
    assert Plan.objects.filter(pk=plan.pk).exists()


def test_an_unused_plan_is_deleted_and_its_name_is_freed(api):
    plan = PlanFactory(name="Temporal")
    assert call(api, "delete", f"/api/v1/plans/{plan.pk}/").status_code == 204
    assert call(api, "get", f"/api/v1/plans/{plan.pk}/").status_code == 404
    assert call(api, "post", "/api/v1/plans/", {**PAYLOAD, "name": "Temporal"}).status_code == 201


def test_a_plan_used_only_by_deleted_tenants_can_be_deleted_logically(api):
    plan = PlanFactory(name="Viejo")
    tenant = TenantFactory(plan=plan)
    call(api, "delete", f"/api/v1/tenants/{tenant.pk}/")
    assert call(api, "delete", f"/api/v1/plans/{plan.pk}/").status_code == 204
    assert Plan.objects.filter(pk=plan.pk, deleted_at__isnull=False).exists()
    assert call(api, "get", "/api/v1/plans/").json() == []


def test_unknown_plan_is_404(api):
    response = call(api, "get", "/api/v1/plans/00000000-0000-0000-0000-000000000000/")
    assert response.status_code == 404
