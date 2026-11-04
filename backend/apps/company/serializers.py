from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.media import services as media
from apps.media.serializers import MediaUrlsSerializer

# Redes que se muestran en la página pública. Cada valor es la URL del perfil.
SOCIAL_NETWORKS = ("instagram", "facebook", "tiktok", "whatsapp", "website")


class LogoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    urls = MediaUrlsSerializer()


class CompanySerializer(serializers.Serializer):
    legal_name = serializers.CharField(max_length=200, allow_blank=True)
    trade_name = serializers.CharField(max_length=200)
    tax_id = serializers.CharField(max_length=30, allow_blank=True, help_text="NIT")
    address = serializers.CharField(max_length=250, allow_blank=True)
    city = serializers.CharField(max_length=100, allow_blank=True)
    phone = serializers.CharField(max_length=30, allow_blank=True)
    email = serializers.EmailField(allow_blank=True)
    logo = serializers.SerializerMethodField()
    terms_html = serializers.CharField(allow_blank=True)
    privacy_html = serializers.CharField(allow_blank=True)
    cookies_html = serializers.CharField(allow_blank=True)
    social_links = serializers.DictField(child=serializers.URLField())

    @extend_schema_field(LogoSerializer(allow_null=True))
    def get_logo(self, company) -> dict | None:
        if company.logo is None:
            return None
        return {"id": company.logo.pk, "urls": media.media_urls(company.logo)}


class CompanyUpdateSerializer(serializers.Serializer):
    """PATCH: todos los campos opcionales. El HTML legal se limpia en el servidor."""

    legal_name = serializers.CharField(max_length=200, allow_blank=True, required=False)
    trade_name = serializers.CharField(max_length=200, required=False)
    tax_id = serializers.CharField(max_length=30, allow_blank=True, required=False)
    address = serializers.CharField(max_length=250, allow_blank=True, required=False)
    city = serializers.CharField(max_length=100, allow_blank=True, required=False)
    phone = serializers.CharField(max_length=30, allow_blank=True, required=False)
    email = serializers.EmailField(allow_blank=True, required=False)
    logo_id = serializers.UUIDField(
        allow_null=True, required=False, help_text="Imagen subida en `media/`; null la quita."
    )
    terms_html = serializers.CharField(allow_blank=True, required=False, trim_whitespace=False)
    privacy_html = serializers.CharField(allow_blank=True, required=False, trim_whitespace=False)
    cookies_html = serializers.CharField(allow_blank=True, required=False, trim_whitespace=False)
    social_links = serializers.DictField(
        child=serializers.URLField(max_length=300),
        required=False,
        help_text=f"Claves permitidas: {', '.join(SOCIAL_NETWORKS)}.",
    )

    def validate_social_links(self, value: dict) -> dict:
        unknown = sorted(set(value) - set(SOCIAL_NETWORKS))
        if unknown:
            raise serializers.ValidationError(f"Redes no permitidas: {', '.join(unknown)}.")
        return value


class LocationSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=150)
    address = serializers.CharField(max_length=250, allow_blank=True, required=False)
    is_default = serializers.BooleanField(required=False)
