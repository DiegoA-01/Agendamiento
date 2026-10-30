from django.db import models

from apps.tenancy.models import TenantOwnedModel


def variant_path(instance: "MediaFile", filename: str) -> str:
    return f"tenants/{instance.tenant_id}/{instance.pk}/{filename}"


class MediaFile(TenantOwnedModel):
    """Imagen subida por un negocio, ya convertida a WebP en tres tamaños (spec §2).

    La conversión y la subida llegan en M4; aquí solo vive el registro que otras apps referencian
    (logo, foto del profesional, imagen del servicio).
    """

    original_name = models.CharField(max_length=255, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    thumb = models.FileField(upload_to=variant_path, blank=True)  # 200 px
    medium = models.FileField(upload_to=variant_path, blank=True)  # 800 px
    large = models.FileField(upload_to=variant_path, blank=True)  # 1600 px

    def __str__(self) -> str:
        return self.original_name or str(self.pk)
