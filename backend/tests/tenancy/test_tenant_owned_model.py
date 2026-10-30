import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.tenancy.context import get_current_tenant, platform_context, tenant_context
from tests.factories import TenantFactory
from tests.testapp.models import Note

pytestmark = pytest.mark.django_db


def test_save_assigns_current_tenant():
    tenant = TenantFactory()
    with tenant_context(tenant):
        note = Note.objects.create(text="hola")
    assert note.tenant_id == tenant.pk


def test_save_without_active_tenant_raises():
    with pytest.raises(ImproperlyConfigured):
        Note.objects.create(text="huérfana")


def test_cannot_save_record_of_another_tenant():
    alfa, beta = TenantFactory(), TenantFactory()
    with tenant_context(alfa):
        note = Note.objects.create(text="mía")
    with tenant_context(beta), pytest.raises(ImproperlyConfigured):
        note.save()


def test_soft_deleted_rows_are_hidden_from_default_manager():
    from django.utils import timezone

    tenant = TenantFactory()
    with tenant_context(tenant):
        note = Note.objects.create(text="borrada")
        Note.objects.filter(pk=note.pk).update(deleted_at=timezone.now())
        assert Note.objects.count() == 0
        assert Note.all_tenants.count() == 1


def test_context_is_cleared_after_block():
    tenant = TenantFactory()
    with tenant_context(tenant):
        assert get_current_tenant() == tenant
    assert get_current_tenant() is None
    with platform_context():
        assert get_current_tenant() is None
