"""Garantías comunes a todas las tablas de negocio (las que heredan de `TenantOwnedModel`)."""

import pytest
from django.apps import apps
from django.db import connection

from apps.tenancy.context import get_current_tenant, tenant_context
from apps.tenancy.models import TenantOwnedModel
from tests.booking.factories import AppointmentItemFactory
from tests.catalog.factories import ProfessionalServiceFactory, ResourceFactory, SpecialtyFactory
from tests.media.factories import MediaFileFactory
from tests.scheduling.factories import TimeBlockFactory, WorkingHoursFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db

BUSINESS_MODELS = [
    model
    for model in apps.get_models()
    if issubclass(model, TenantOwnedModel) and model._meta.app_label != "testapp"
]


@pytest.mark.parametrize("model", BUSINESS_MODELS, ids=lambda m: m._meta.db_table)
def test_every_business_table_has_row_level_security_enabled_and_forced(model):
    """Una tabla de negocio sin `enable_rls(...)` en su migración rompe este test."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = %s",
            [model._meta.db_table],
        )
        assert cursor.fetchone() == (True, True)


def _create_one_of_each():
    """Crea al menos una fila en cada tabla de negocio nueva del tenant activo."""
    MediaFileFactory()
    ResourceFactory()
    link = ProfessionalServiceFactory()
    link.professional.specialties.add(
        SpecialtyFactory(), through_defaults={"tenant": get_current_tenant()}
    )
    WorkingHoursFactory()
    TimeBlockFactory()
    AppointmentItemFactory()


def test_business_rows_are_invisible_to_other_tenants_even_without_the_orm_filter():
    alfa, beta = TenantFactory(), TenantFactory()
    with tenant_context(alfa):
        _create_one_of_each()

    with tenant_context(beta):
        for model in BUSINESS_MODELS:
            assert not model.all_tenants.exists(), model._meta.db_table
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT count(*) FROM "{model._meta.db_table}"')
                assert cursor.fetchone()[0] == 0, model._meta.db_table

    with tenant_context(alfa):
        for model in BUSINESS_MODELS:
            if model._meta.db_table == "company_company":
                continue  # la empresa la crea el alta del negocio, no estas factories
            assert model.objects.exists(), model._meta.db_table
