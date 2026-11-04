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


class SpecialtySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)


PERCENT = {
    "max_digits": 5,
    "decimal_places": 2,
    "min_value": Decimal("0"),
    "max_value": Decimal("100"),
}


class ProfessionalSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    display_name = serializers.CharField(max_length=150)
    bio = serializers.CharField(allow_blank=True, required=False)
    user_id = serializers.UUIDField(
        allow_null=True, required=False, help_text="Cuenta del negocio que usa esta ficha."
    )
    location_id = serializers.UUIDField(
        required=False, help_text="Sin indicarla se usa la sede por defecto."
    )
    photo_id = serializers.UUIDField(
        allow_null=True, required=False, write_only=True, help_text="Imagen subida en `media/`."
    )
    photo = serializers.SerializerMethodField()
    specialty_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    default_commission_pct = serializers.DecimalField(**PERCENT, required=False)
    is_active = serializers.BooleanField(required=False)
    accepts_online_booking = serializers.BooleanField(required=False)

    @extend_schema_field(ImageSerializer(allow_null=True))
    def get_photo(self, professional) -> dict | None:
        return _image(professional.photo)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # `catalog.services.with_specialties` deja la lista en la ficha con una sola consulta.
        data["specialty_ids"] = [str(value) for value in instance.specialty_id_list]
        return data


class OfferedServiceSerializer(serializers.Serializer):
    """Servicio que ofrece el profesional. Un override en null usa el valor del servicio (o la
    comisión por defecto del profesional)."""

    service_id = serializers.UUIDField()
    service_name = serializers.CharField(source="service.name", read_only=True)
    price_override = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    commission_pct_override = serializers.DecimalField(**PERCENT, allow_null=True, required=False)
    duration_override_min = serializers.IntegerField(
        min_value=5, max_value=24 * 60, allow_null=True, required=False
    )


class OfferedServicesSerializer(serializers.Serializer):
    services = OfferedServiceSerializer(many=True)
