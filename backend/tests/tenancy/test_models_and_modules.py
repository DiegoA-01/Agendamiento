import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client

from apps.tenancy import services
from apps.tenancy.constants import MODULE_KEYS, RESERVED_SLUGS
from apps.tenancy.models import Domain, Plan, Tenant, TenantModule
from tests.tenancy.factories import PlanFactory, TenantFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("slug", sorted(RESERVED_SLUGS))
def test_reserved_slugs_are_rejected_even_on_save(slug):
    with pytest.raises(ValidationError):
        Tenant(name="X", slug=slug, plan=PlanFactory()).save()


@pytest.mark.parametrize("slug", ["Con Espacio", "-guion", "guion-", "ñandú", "a" * 64])
def test_invalid_slugs_are_rejected(slug):
    with pytest.raises(ValidationError):
        Tenant(name="X", slug=slug, plan=PlanFactory()).save()


def test_tenant_defaults():
    tenant = TenantFactory()
    assert (tenant.timezone, tenant.currency, tenant.language) == ("America/Bogota", "COP", "es")
    assert tenant.status == Tenant.Status.ACTIVE
    assert tenant.theme == {}


def test_invalid_timezone_is_rejected():
    tenant = Tenant(name="X", slug="zona", plan=PlanFactory(), timezone="Marte/Olimpo")
    with pytest.raises(ValidationError):
        tenant.full_clean()


def test_plan_rejects_unknown_modules():
    with pytest.raises(ValidationError):
        Plan(name="Raro", modules=["booking", "teletransporte"]).full_clean()


def test_domain_host_is_normalized_and_token_is_generated():
    tenant = TenantFactory(with_domain=False)
    a = Domain.objects.create(tenant=tenant, host="  WWW.Mi-Sitio.COM. ")
    b = Domain.objects.create(tenant=tenant, host="otro.com")
    assert a.host == "www.mi-sitio.com"
    assert a.verified is False
    assert a.verification_token and a.verification_token != b.verification_token


def test_domain_host_is_unique():
    tenant = TenantFactory(with_domain=False)
    Domain.objects.create(tenant=tenant, host="x.com")
    with pytest.raises(IntegrityError), transaction.atomic():
        Domain.objects.create(tenant=tenant, host="X.com")


def test_ensure_subdomain_is_idempotent_and_verified():
    tenant = TenantFactory(slug="elfilo", with_domain=False)
    first = services.ensure_subdomain(tenant)
    assert services.ensure_subdomain(tenant) == first
    assert first.host == f"elfilo.{settings.BASE_DOMAIN}"
    assert first.verified is True


def test_sync_modules_follows_plan_and_is_idempotent():
    plan = PlanFactory(modules=["booking", "reports"])
    tenant = TenantFactory(plan=plan)
    assert services.enabled_module_keys(tenant) == {"booking", "reports"}

    plan.modules = ["booking", "commissions"]
    plan.save()
    services.sync_modules_from_plan(tenant)
    services.sync_modules_from_plan(tenant)
    assert services.enabled_module_keys(tenant) == {"booking", "commissions"}
    assert TenantModule.objects.filter(tenant=tenant).count() == len(MODULE_KEYS)


def test_modules_are_per_tenant():
    inicial = TenantFactory(plan=PlanFactory(modules=["booking"]))
    pro = TenantFactory(plan=PlanFactory(modules=list(MODULE_KEYS)))
    assert services.is_module_enabled(inicial, "commissions") is False
    assert services.is_module_enabled(pro, "commissions") is True
    assert services.is_module_enabled(None, "booking") is False


def test_requires_module_allows_tenant_with_module():
    TenantFactory(slug="conbooking", plan=PlanFactory(modules=["booking"]))
    response = Client().get("/test/booking-only/", HTTP_HOST=f"conbooking.{settings.BASE_DOMAIN}")
    assert response.status_code == 200


def test_requires_module_blocks_tenant_without_module():
    TenantFactory(slug="sinbooking", plan=PlanFactory(modules=["reports"]))
    response = Client().get("/test/booking-only/", HTTP_HOST=f"sinbooking.{settings.BASE_DOMAIN}")
    assert response.status_code == 403
    assert response.json()["code"] == "module_disabled"


def test_requires_module_blocks_platform_admin_host():
    response = Client().get("/test/booking-only/", HTTP_HOST=f"admin.{settings.BASE_DOMAIN}")
    assert response.status_code == 403
