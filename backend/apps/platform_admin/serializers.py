from rest_framework import serializers

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
