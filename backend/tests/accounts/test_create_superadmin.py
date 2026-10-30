import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from tests.factories import PASSWORD

pytestmark = pytest.mark.django_db


def test_creates_a_superadmin_without_tenant():
    call_command("create_superadmin", email="Root@Ejemplo.com", password=PASSWORD, name="Raíz")
    user = User.objects.get(email="root@ejemplo.com")
    assert user.role == User.Role.SUPERADMIN
    assert user.tenant is None
    assert user.full_name == "Raíz"
    assert user.check_password(PASSWORD)
    assert user.totp_enabled is False


def test_refuses_duplicates():
    call_command("create_superadmin", email="root@x.com", password=PASSWORD)
    with pytest.raises(CommandError, match="Ya existe"):
        call_command("create_superadmin", email="root@x.com", password=PASSWORD)


def test_refuses_weak_passwords():
    with pytest.raises(CommandError):
        call_command("create_superadmin", email="root@x.com", password="12345678")
    assert not User.objects.exists()
