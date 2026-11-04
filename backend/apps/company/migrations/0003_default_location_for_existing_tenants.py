"""Crea la sede por defecto a los negocios que se dieron de alta antes de que existiera.

Desde esta versión `company.services.create_company` la crea con el negocio; los anteriores no la
tienen, y sin sede no se pueden crear profesionales ni puestos. La migración corre con el rol de la
app, que está sujeto a RLS: activa el modo plataforma solo mientras dura.
"""

from django.db import migrations

DEFAULT_LOCATION_NAME = {"es": "Sede principal", "en": "Main location"}


def _bypass_rls(schema_editor, value: str) -> None:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.bypass_rls', %s, false)", [value])


def create_missing_default_locations(apps, schema_editor):
    Tenant = apps.get_model("tenancy", "Tenant")
    Location = apps.get_model("company", "Location")
    _bypass_rls(schema_editor, "on")
    try:
        # `_base_manager` no filtra por tenant (igual que el manager de un modelo histórico).
        locations = Location._base_manager
        with_default = locations.filter(
            is_default=True, deleted_at__isnull=True
        ).values_list("tenant_id", flat=True)
        for tenant in Tenant.objects.filter(deleted_at__isnull=True).exclude(pk__in=with_default):
            locations.create(
                tenant=tenant,
                name=DEFAULT_LOCATION_NAME.get(tenant.language, DEFAULT_LOCATION_NAME["es"]),
                is_default=True,
            )
    finally:
        _bypass_rls(schema_editor, "")


class Migration(migrations.Migration):
    dependencies = [
        ("company", "0002_company_logo_location"),
        ("tenancy", "0002_tenant_agenda_settings"),
    ]

    # Al revertir no se borra nada: las sedes ya pueden tener profesionales enlazados.
    operations = [
        migrations.RunPython(create_missing_default_locations, migrations.RunPython.noop),
    ]
