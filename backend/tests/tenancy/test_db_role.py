import pytest
from django.db import connection

pytestmark = pytest.mark.django_db


def test_app_role_cannot_bypass_rls():
    """Si el rol de la app fuera superusuario o BYPASSRLS, RLS no protegería nada y ningún test de
    aislamiento lo notaría. Este test lo detecta (p. ej. un CI sin crear el rol sin privilegios)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        rolsuper, rolbypassrls = cursor.fetchone()
    assert rolsuper is False
    assert rolbypassrls is False
