"""La ventana para cancelar por enlace pasa de 2 h a 1 h por defecto.

Decisión del equipo (2026-11-12): el cliente puede cancelar su cita hasta 1 hora antes. Los negocios
que seguían con el valor anterior por defecto (2 h) pasan a 1 h; uno que eligió otro valor lo
conserva. La tabla de negocios no tiene RLS, así que no hace falta el modo plataforma.
"""

from django.db import migrations, models
from django.core.validators import MaxValueValidator


def to_one_hour(apps, schema_editor):
    Tenant = apps.get_model("tenancy", "Tenant")
    Tenant.objects.filter(cancel_min_hours=2).update(cancel_min_hours=1)


def back_to_two_hours(apps, schema_editor):
    Tenant = apps.get_model("tenancy", "Tenant")
    Tenant.objects.filter(cancel_min_hours=1).update(cancel_min_hours=2)


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0002_tenant_agenda_settings")]

    operations = [
        migrations.AlterField(
            model_name="tenant",
            name="cancel_min_hours",
            field=models.PositiveSmallIntegerField(
                default=1, validators=[MaxValueValidator(24 * 7)]
            ),
        ),
        migrations.RunPython(to_one_hour, back_to_two_hours),
    ]
