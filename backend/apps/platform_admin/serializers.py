from rest_framework import serializers

from apps.accounts.models import User
from apps.tenancy import services as tenancy
from apps.tenancy.constants import LANGUAGES, MODULE_KEYS, VERTICALS
from apps.tenancy.theme import THEME_KEYS


def _module_choice() -> serializers.ChoiceField:
    # Una instancia nueva por uso: DRF liga cada campo a un solo serializador.
    return serializers.ChoiceField(choices=MODULE_KEYS)


class PlanSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    modules = serializers.ListField(child=_module_choice())
    max_professionals = serializers.IntegerField()
    max_locations = serializers.IntegerField()


class PlanBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class PlanWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    modules = serializers.ListField(child=_module_choice(), allow_empty=True)
    max_professionals = serializers.IntegerField(min_value=1)
    max_locations = serializers.IntegerField(min_value=1)


class PlanUpdateSerializer(PlanWriteSerializer):
    # Aplica los módulos del plan a los negocios que ya lo usan (sobrescribe ajustes manuales).
    apply_to_tenants = serializers.BooleanField(required=False)


class TenantSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    vertical = serializers.CharField()
    timezone = serializers.CharField()
    currency = serializers.CharField()
    language = serializers.CharField()
    status = serializers.CharField()
    theme = serializers.DictField()
    created_at = serializers.DateTimeField()
    plan = PlanBriefSerializer()


class TenantDetailSerializer(TenantSerializer):
    modules = serializers.SerializerMethodField()

    def get_modules(self, tenant) -> list[str]:
        return sorted(tenancy.enabled_module_keys(tenant))


class TenantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=63)
    plan_id = serializers.UUIDField()
    vertical = serializers.ChoiceField(choices=VERTICALS, default="barbershop")
    timezone = serializers.CharField(default="America/Bogota")
    currency = serializers.CharField(max_length=3, default="COP")
    language = serializers.ChoiceField(choices=LANGUAGES, default="es")
    owner_email = serializers.EmailField()
    owner_name = serializers.CharField(max_length=150)
    # S5. La contraseña sigue siendo temporal: el Super Admin nunca conoce la definitiva.
    owner_phone = serializers.RegexField(
        r"^\+?[\d\s-]{7,20}$", required=False, allow_blank=True, default=""
    )
    owner_document_type = serializers.ChoiceField(
        choices=User.DocumentType.choices, required=False, allow_blank=True, default=""
    )
    owner_document_number = serializers.RegexField(
        r"^[A-Za-z0-9]{3,20}$", required=False, allow_blank=True, default=""
    )
    tax_id = serializers.RegexField(
        r"^\d{6,12}(-\d)?$",
        required=False,
        allow_blank=True,
        default="",
        help_text="NIT o RUT, con o sin dígito de verificación: 900123456-7.",
    )

    def validate_owner_phone(self, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if value and not 7 <= len(digits) <= 15:
            raise serializers.ValidationError("Escribe un celular válido (7 a 15 dígitos).")
        return value.strip()

    def validate(self, attrs):
        kind, number = attrs.get("owner_document_type"), attrs.get("owner_document_number")
        if bool(kind) != bool(number):
            field = "owner_document_number" if kind else "owner_document_type"
            raise serializers.ValidationError({field: ["Indica el tipo y el número de documento."]})
        if kind == "CC" and not number.isdigit():
            raise serializers.ValidationError(
                {"owner_document_number": ["La cédula solo lleva números."]}
            )
        return attrs


class TenantCreatedSerializer(serializers.Serializer):
    tenant = TenantDetailSerializer()
    owner = serializers.DictField(child=serializers.CharField())
    temporary_password = serializers.CharField()


class TenantUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    plan_id = serializers.UUIDField()
    vertical = serializers.ChoiceField(choices=VERTICALS)
    timezone = serializers.CharField()
    currency = serializers.CharField(max_length=3)
    language = serializers.ChoiceField(choices=LANGUAGES)


class ThemeSerializer(serializers.Serializer):
    """Solo documenta el formato; la validación (hex y contraste) vive en tenancy.theme."""

    primary = serializers.CharField()
    secondary = serializers.CharField()
    background = serializers.CharField()
    surface = serializers.CharField()
    text = serializers.CharField()


assert set(ThemeSerializer().fields) == set(THEME_KEYS)


class ModulesWriteSerializer(serializers.Serializer):
    modules = serializers.DictField(child=serializers.BooleanField())


class ModulesSerializer(serializers.Serializer):
    available = serializers.ListField(child=serializers.CharField())
    enabled = serializers.ListField(child=serializers.CharField())


class DomainCreateSerializer(serializers.Serializer):
    host = serializers.CharField(max_length=253)


class DomainSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    host = serializers.CharField()
    kind = serializers.CharField()
    verified = serializers.BooleanField()
    verification_token = serializers.CharField()
    created_at = serializers.DateTimeField()
    instructions = serializers.SerializerMethodField()

    def get_instructions(self, domain) -> dict:
        return tenancy.dns_instructions(domain)


class DomainVerificationSerializer(serializers.Serializer):
    verified = serializers.BooleanField()
    txt_ok = serializers.BooleanField()
    cname_ok = serializers.BooleanField()


class AuditLogSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action = serializers.CharField()
    entity = serializers.CharField()
    entity_id = serializers.CharField()
    before = serializers.JSONField(allow_null=True)
    after = serializers.JSONField(allow_null=True)
    ip = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    actor_email = serializers.SerializerMethodField()
    tenant_id = serializers.UUIDField(allow_null=True)
    tenant_name = serializers.SerializerMethodField()

    def get_actor_email(self, log) -> str | None:
        return log.actor.email if log.actor else None

    def get_tenant_name(self, log) -> str | None:
        return log.tenant.name if log.tenant else None


class TenantUsageSerializer(serializers.Serializer):
    """Uso del sistema por negocio (S10).

    `*_recent` cuenta las citas creadas en los últimos `window_days` días.
    """

    window_days = serializers.IntegerField()
    appointments_total = serializers.IntegerField()
    appointments_recent = serializers.IntegerField()
    web_bookings_recent = serializers.IntegerField()
    completed_recent = serializers.IntegerField()
    cancelled_recent = serializers.IntegerField()
    customers_total = serializers.IntegerField()
    users_active = serializers.IntegerField()
    last_login = serializers.DateTimeField(allow_null=True)


class IntegrationChannelSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=["whatsapp", "email"])
    sent = serializers.IntegerField()
    failed = serializers.IntegerField()
    queued = serializers.IntegerField()
    last_sent_at = serializers.DateTimeField(allow_null=True)


class IntegrationFailureSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField()
    kind = serializers.CharField()
    channel = serializers.CharField()
    to = serializers.CharField()
    attempts = serializers.IntegerField()
    error = serializers.CharField(max_length=300, allow_blank=True)


class TenantIntegrationsSerializer(serializers.Serializer):
    """Integraciones del negocio (S11).

    Cuenta registros creados en los últimos `window_days` días; destinatarios enmascarados.
    """

    window_days = serializers.IntegerField()
    whatsapp_enabled = serializers.BooleanField()
    whatsapp_provider = serializers.ChoiceField(choices=["fake", "cloud_api", "other"])
    whatsapp_configured = serializers.BooleanField()
    email_backend = serializers.CharField()
    channels = IntegrationChannelSerializer(many=True)
    recent_failures = IntegrationFailureSerializer(many=True)
