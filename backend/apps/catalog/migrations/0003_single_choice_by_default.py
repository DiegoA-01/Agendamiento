""""Solo uno por cita" pasa a estar activo por defecto, también en las categorías que ya existen.

Nadie se hace dos cortes, dos barbas ni dos depilaciones en la misma cita. Si un negocio quiere
permitir varios servicios de una categoría, lo apaga en el catálogo. La migración corre con el rol de
la app, sujeto a RLS: activa el modo plataforma solo mientras dura (ver company/0003).
"""

from django.db import migrations, models


def _bypass_rls(schema_editor, value: str) -> None:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.bypass_rls', %s, false)", [value])


def turn_on_everywhere(apps, schema_editor):
    ServiceCategory = apps.get_model("catalog", "ServiceCategory")
    _bypass_rls(schema_editor, "on")
    try:
        ServiceCategory._base_manager.filter(single_choice=False).update(single_choice=True)
    finally:
        _bypass_rls(schema_editor, "")


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_category_single_choice")]

    # Al revertir no se vuelve a apagar: no se sabe cuáles estaban apagadas a propósito.
    operations = [
        migrations.AlterField(
            model_name="servicecategory",
            name="single_choice",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(turn_on_everywhere, migrations.RunPython.noop),
    ]
