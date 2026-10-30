"""Prueba obligatoria de M1 (spec §4.9): dos tenants, ningún dato cruza, con RLS activo y con el
manager sin filtrar."""

import pytest
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.test import Client

from apps.tenancy.context import platform_context, tenant_context
from tests.tenancy.factories import TenantFactory
from tests.testapp.models import Note

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_tenants():
    alfa, beta = TenantFactory(slug="alfa"), TenantFactory(slug="beta")
    with tenant_context(alfa):
        Note.objects.create(text="alfa-1")
        Note.objects.create(text="alfa-2")
    with tenant_context(beta):
        Note.objects.create(text="beta-1")
    return alfa, beta


def host(slug: str) -> str:
    return f"{slug}.{settings.BASE_DOMAIN}"


def raw_count() -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM testapp_note")
        return cursor.fetchone()[0]


@pytest.mark.parametrize("path", ["/test/notes/", "/test/notes-unfiltered/"])
@pytest.mark.parametrize(
    ("slug", "expected"),
    [("alfa", ["alfa-1", "alfa-2"]), ("beta", ["beta-1"])],
)
def test_endpoints_only_return_own_data(two_tenants, path, slug, expected):
    """`notes-unfiltered` usa el manager sin filtro: aquí el aislamiento lo da RLS."""
    response = Client().get(path, HTTP_HOST=host(slug))
    assert response.status_code == 200
    assert response.json() == {"notes": expected}


def test_raw_sql_is_isolated_by_rls(two_tenants):
    alfa, beta = two_tenants
    with tenant_context(alfa):
        assert raw_count() == 2
    with tenant_context(beta):
        assert raw_count() == 1


def test_no_active_tenant_sees_nothing(two_tenants):
    assert raw_count() == 0
    assert list(Note.objects.all()) == []
    assert list(Note.all_tenants.all()) == []


def test_platform_context_sees_all_tenants(two_tenants):
    with platform_context():
        assert raw_count() == 3
        assert Note.all_tenants.count() == 3


def test_rls_blocks_cross_tenant_insert(two_tenants):
    """bulk_create no pasa por save(): aquí solo protege el WITH CHECK de la política."""
    alfa, beta = two_tenants
    with tenant_context(alfa), pytest.raises(DatabaseError), transaction.atomic():
        Note.all_tenants.bulk_create([Note(text="intruso", tenant=beta)])


def test_rls_blocks_cross_tenant_update_and_delete(two_tenants):
    alfa, _ = two_tenants
    with tenant_context(alfa):
        assert Note.all_tenants.filter(text="beta-1").update(text="hackeado") == 0
        assert Note.all_tenants.filter(text="beta-1").delete()[0] == 0
    with platform_context():
        assert Note.all_tenants.filter(text="beta-1").count() == 1


def test_tenant_context_restores_previous_tenant(two_tenants):
    alfa, beta = two_tenants
    with tenant_context(alfa):
        with tenant_context(beta):
            assert raw_count() == 1
        assert raw_count() == 2
    assert raw_count() == 0
