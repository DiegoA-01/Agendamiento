from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.media import services as media
from apps.media.serializers import MediaUrlsSerializer


class ImageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    urls = MediaUrlsSerializer()


def _image(instance) -> dict | None:
    if instance is None:
        return None
    return {"id": instance.pk, "urls": media.media_urls(instance)}


class CategorySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    sort_order = serializers.IntegerField(min_value=0, required=False)


class ServiceSerializer(serializers.Serializer):
    """Precio como texto decimal (`"30000.00"`), en la moneda del negocio."""

    id = serializers.UUIDField(read_only=True)
    category_id = serializers.UUIDField()
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(allow_blank=True, required=False)
    duration_min = serializers.IntegerField(min_value=5, max_value=24 * 60)
    buffer_min = serializers.IntegerField(min_value=0, max_value=240, required=False)
    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), coerce_to_string=True
    )
    is_active = serializers.BooleanField(required=False)
    requires_resource = serializers.BooleanField(required=False)
    image_id = serializers.UUIDField(
        allow_null=True,
        required=False,
        write_only=True,
        help_text="Imagen subida en `media/`; null la quita.",
    )
    image = serializers.SerializerMethodField()

    @extend_schema_field(ImageSerializer(allow_null=True))
    def get_image(self, service) -> dict | None:
        return _image(service.image)


class ResourceSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    kind = serializers.CharField(max_length=50, allow_blank=True, required=False)
    is_active = serializers.BooleanField(required=False)
    location_id = serializers.UUIDField(
        required=False, help_text="Sin indicarla se usa la sede por defecto."
    )
