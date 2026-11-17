"""Estilo de la página pública de reservas. Los negocios que ya existen quedan en `emerald` (el
estilo que tenían); los nuevos arrancan vacíos y toman el estilo de su tipo de negocio."""

from django.db import migrations, models

STYLE_CHOICES = [("emerald", "Esmeralda"), ("barbershop", "Barbería clásica"), ("salon", "Salón")]


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0003_cancel_window_one_hour"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="public_style",
            field=models.CharField(
                blank=True, choices=STYLE_CHOICES, default="emerald", max_length=20
            ),
        ),
        migrations.AlterField(
            model_name="tenant",
            name="public_style",
            field=models.CharField(blank=True, choices=STYLE_CHOICES, default="", max_length=20),
        ),
    ]
