"""Tenant activo de la petición/tarea y su reflejo en PostgreSQL (para RLS).

El tenant vive en un ContextVar (cada petición ve el suyo) y se copia al parámetro de sesión
`app.current_tenant`, que leen las políticas RLS. Se usa `set_config(..., false)` (sesión) en lugar
de `SET LOCAL` porque Django corre en autocommit y `SET LOCAL` fuera de una transacción no hace
nada; siempre se restaura al salir del contexto.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from django.db import connection

from .constants import DB_SETTING_BYPASS, DB_SETTING_TENANT

if TYPE_CHECKING:
    from .models import Tenant

_current_tenant: ContextVar["Tenant | None"] = ContextVar("current_tenant", default=None)


def get_current_tenant() -> "Tenant | None":
    return _current_tenant.get()


def _set_db_setting(name: str, value: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, false)", [name, value])


@contextmanager
def tenant_context(tenant: "Tenant") -> Iterator["Tenant"]:
    """Activa `tenant` para el código del bloque (ORM y RLS). Pensado también para tareas Celery."""
    previous = _current_tenant.get()
    _current_tenant.set(tenant)
    _set_db_setting(DB_SETTING_TENANT, str(tenant.pk))
    try:
        yield tenant
    finally:
        _set_db_setting(DB_SETTING_TENANT, str(previous.pk) if previous else "")
        _current_tenant.set(previous)


@contextmanager
def platform_context() -> Iterator[None]:
    """Acceso entre tenants (Super Admin y tareas globales): las políticas RLS dejan pasar todo.

    Se usa junto con el manager `all_tenants`. Nunca desde peticiones de un tenant.
    """
    _set_db_setting(DB_SETTING_BYPASS, "on")
    try:
        yield
    finally:
        _set_db_setting(DB_SETTING_BYPASS, "")
