"""Serializadores de la reserva pública (M6). Nunca exponen datos internos: ni celulares de otros
clientes, ni comisiones, ni ids de usuarios."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.media import services as media

from .models import Appointment


class ImageUrlsSerializer(serializers.Serializer):
    thumb = serializers.CharField(required=False)
    medium = serializers.CharField(required=False)
    large = serializers.CharField(required=False)


class PublicCompanySerializer(serializers.Serializer):
    name = serializers.CharField()
    vertical = serializers.CharField()
    language = serializers.CharField()
    timezone = serializers.CharField()
    currency = serializers.CharField()
    theme = serializers.DictField(child=serializers.CharField())
    logo = ImageUrlsSerializer(allow_null=True)
    address = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    email = serializers.CharField(allow_blank=True)
    social_links = serializers.DictField(child=serializers.CharField())
    terms_html = serializers.CharField(allow_blank=True)
    privacy_html = serializers.CharField(allow_blank=True)
    cookies_html = serializers.CharField(allow_blank=True)
    cancel_min_hours = serializers.IntegerField()
    booking_enabled = serializers.BooleanField()


class PublicServiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    duration_min = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    image = serializers.SerializerMethodField()

    @extend_schema_field(ImageUrlsSerializer(allow_null=True))
    def get_image(self, service):
        return media.media_urls(service.image)


class PublicCategorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    services = PublicServiceSerializer(many=True)


class PublicProfessionalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    bio = serializers.CharField()
    photo = serializers.SerializerMethodField()

    @extend_schema_field(ImageUrlsSerializer(allow_null=True))
    def get_photo(self, professional):
        return media.media_urls(professional.photo)


class PublicCustomerSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30)
    email = serializers.EmailField(required=False, allow_blank=True, default="")


class PublicBookingSerializer(serializers.Serializer):
    """`professional_id` vacío = cualquiera. `website` es el honeypot: debe ir vacío."""

    service_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=10)
    professional_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    start_at = serializers.DateTimeField()
    customer = PublicCustomerSerializer()
    accept_data_policy = serializers.BooleanField(
        help_text="Autorización de tratamiento de datos (Ley 1581). Debe ser true."
    )
    marketing_consent = serializers.BooleanField(required=False, default=False)
    website = serializers.CharField(required=False, allow_blank=True, default="")
    captcha_token = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_accept_data_policy(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar la política de tratamiento de datos.")
        return value


class PublicItemSerializer(serializers.Serializer):
    name = serializers.CharField(source="service.name")
    duration_min = serializers.IntegerField()
    price = serializers.DecimalField(source="price_charged", max_digits=12, decimal_places=2)


class PublicAppointmentSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Appointment.Status.choices)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    professional = serializers.CharField(source="professional.display_name")
    location = serializers.CharField(source="location.name")
    address = serializers.CharField(source="location.address")
    customer_name = serializers.CharField(source="customer.full_name")
    items = PublicItemSerializer(many=True, source="items.all")
    price_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    can_cancel = serializers.BooleanField()
    cancel_deadline = serializers.DateTimeField()


class PublicBookedSerializer(PublicAppointmentSerializer):
    manage_url = serializers.CharField(help_text="Enlace para ver o cancelar la cita.")


class PublicCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=250, required=False, allow_blank=True, default="")
