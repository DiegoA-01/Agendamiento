import importlib

import pytest
from django.apps import apps as django_apps
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.company import services as company
from apps.company.models import Location
from apps.tenancy.context import platform_context, tenant_context
from tests.catalog.factories import ProfessionalFactory
from tests.company.factories import LocationFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db

migration = importlib.import_module(
    "apps.company.migrations.0003_default_location_for_existing_tenants"
)


def test_creating_a_company_creates_its_default_location():
    tenant = TenantFactory()
    company.create_company(tenant)

    location = company.get_default_location(tenant)
    assert location is not None
    assert location.name == "Sede principal"
    assert location.tenant_id == tenant.pk


def test_the_default_location_is_named_in_the_business_language():
    tenant = TenantFactory(language="en")
    company.create_company(tenant)
    assert company.get_default_location(tenant).name == "Main location"


def test_a_new_business_can_create_a_professional_right_away():
    """El motivo de la sede por defecto: profesionales y puestos exigen una."""
    tenant = TenantFactory()
    company.create_company(tenant)
    with tenant_context(tenant):
        professional = ProfessionalFactory(location=company.get_default_location(tenant))
    assert professional.location.is_default


def test_each_business_gets_its_own_default_location():
    alfa, beta = TenantFactory(), TenantFactory()
    company.create_company(alfa)
    company.create_company(beta)
    assert company.get_default_location(alfa) != company.get_default_location(beta)
    with tenant_context(alfa):
        assert Location.objects.count() == 1


def test_only_one_default_location_per_business():
    tenant = TenantFactory()
    company.create_company(tenant)
    with tenant_context(tenant), pytest.raises(IntegrityError), transaction.atomic():
        Location.objects.create(name="Otra principal", is_default=True)


def test_a_deleted_default_location_frees_the_slot():
    tenant = TenantFactory()
    old = LocationFactory(tenant=tenant, is_default=True)
    with tenant_context(tenant):
        Location.objects.filter(pk=old.pk).update(deleted_at=timezone.now())
    LocationFactory(tenant=tenant, is_default=True)


class _SchemaEditor:
    connection = connection


def test_the_migration_gives_a_default_location_to_businesses_that_lack_one():
    without = TenantFactory(language="en")
    already = TenantFactory()
    LocationFactory(tenant=already, is_default=True, name="Centro")

    migration.create_missing_default_locations(django_apps, _SchemaEditor())
    # Correrla dos veces no duplica nada.
    migration.create_missing_default_locations(django_apps, _SchemaEditor())

    assert company.get_default_location(without).name == "Main location"
    assert company.get_default_location(already).name == "Centro"
    with platform_context():
        assert Location.all_tenants.filter(tenant=without).count() == 1
        assert Location.all_tenants.filter(tenant=already).count() == 1
