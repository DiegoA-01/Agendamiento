import pytest
from django.db import IntegrityError, connection, transaction

from apps.company import services as company
from apps.company.models import Company
from apps.tenancy.context import platform_context, tenant_context
from tests.factories import TenantFactory

pytestmark = pytest.mark.django_db


def test_create_company_uses_the_business_name_by_default():
    tenant = TenantFactory(name="Barbería El Filo")
    created = company.create_company(tenant)
    assert created.trade_name == "Barbería El Filo"
    assert created.tenant_id == tenant.pk
    assert company.get_company(tenant) == created


def test_only_one_company_per_tenant():
    tenant = TenantFactory()
    company.create_company(tenant)
    with tenant_context(tenant), pytest.raises(IntegrityError), transaction.atomic():
        Company.objects.create(trade_name="Duplicada")


def test_a_database_error_inside_the_context_is_not_masked_by_the_cleanup():
    """Regresión: con la transacción rota, restaurar el tenant lanzaba otro error que tapaba el
    IntegrityError real."""
    tenant = TenantFactory()
    company.create_company(tenant)
    with pytest.raises(IntegrityError), transaction.atomic(), tenant_context(tenant):
        Company.objects.create(trade_name="Duplicada")


def test_a_company_is_invisible_to_other_tenants_by_orm_and_by_rls():
    alfa, beta = TenantFactory(), TenantFactory()
    company.create_company(alfa, trade_name="Alfa")
    company.create_company(beta, trade_name="Beta")

    with tenant_context(alfa):
        assert [c.trade_name for c in Company.objects.all()] == ["Alfa"]
        # Manager sin filtro: aquí protege RLS.
        assert [c.trade_name for c in Company.all_tenants.all()] == ["Alfa"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM company_company")
            assert cursor.fetchone()[0] == 1
    assert company.get_company(beta).trade_name == "Beta"
    with platform_context():
        assert Company.all_tenants.count() == 2
    assert Company.all_tenants.count() == 0  # sin tenant activo no se ve nada


def test_company_table_has_row_level_security_enabled_and_forced():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relname = 'company_company'"
        )
        assert cursor.fetchone() == (True, True)
