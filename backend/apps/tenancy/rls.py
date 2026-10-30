"""Row Level Security para tablas de negocio (las que heredan de `TenantOwnedModel`).

Uso en la migración de cada modelo de negocio:

    from apps.tenancy.rls import enable_rls

    operations = [..., enable_rls("booking_customer")]

La política deja ver una fila solo si su `tenant_id` es el tenant activo de la sesión, o si la
sesión está en modo plataforma (`platform_context`). Sin tenant activo no se ve ninguna fila.
FORCE hace que la política aplique también al dueño de la tabla (el rol de la app es el dueño).
"""

from django.db import migrations

POLICY_NAME = "tenant_isolation"

_CONDITION = (
    "current_setting('app.bypass_rls', true) = 'on' "
    "OR tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"
)


def enable_rls_sql(table: str) -> list[str]:
    return [
        f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY',
        f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY',
        f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"',
        f'CREATE POLICY {POLICY_NAME} ON "{table}" USING ({_CONDITION}) WITH CHECK ({_CONDITION})',
    ]


def disable_rls_sql(table: str) -> list[str]:
    return [
        f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"',
        f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY',
        f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY',
    ]


def enable_rls(table: str) -> migrations.RunSQL:
    return migrations.RunSQL(sql=enable_rls_sql(table), reverse_sql=disable_rls_sql(table))
