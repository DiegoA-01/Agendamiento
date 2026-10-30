import re
import secrets
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models

from .constants import MODULE_KEYS, RESERVED_SLUGS
from .context import get_current_tenant

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


def validate_slug(value: str) -> None:
    if not _SLUG_RE.match(value):
        raise ValidationError("El slug solo admite minúsculas, números y guiones.", code="invalid")
    if value in RESERVED_SLUGS:
        raise ValidationError("Este subdominio está reservado.", code="reserved")


def validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValidationError("Zona horaria inválida.", code="invalid") from exc


def _new_token() -> str:
    return secrets.token_urlsafe(24)


class BaseModel(models.Model):
    """Convención de la spec: UUID, fechas en UTC y borrado lógico."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class Plan(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    modules = models.JSONField(default=list, blank=True)
    max_professionals = models.PositiveIntegerField(default=1)
    max_locations = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        unknown = set(self.modules) - set(MODULE_KEYS)
        if unknown:
            raise ValidationError({"modules": f"Módulos desconocidos: {sorted(unknown)}"})


class Tenant(BaseModel):
    class Vertical(models.TextChoices):
        BARBERSHOP = "barbershop"
        SALON = "salon"
        NAILS = "nails"
        SPA = "spa"

    class Status(models.TextChoices):
        ACTIVE = "active"
        SUSPENDED = "suspended"

    class Language(models.TextChoices):
        ES = "es"
        EN = "en"

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=63, unique=True, validators=[validate_slug])
    vertical = models.CharField(
        max_length=20, choices=Vertical.choices, default=Vertical.BARBERSHOP
    )
    timezone = models.CharField(
        max_length=64, default="America/Bogota", validators=[validate_timezone]
    )
    currency = models.CharField(max_length=3, default="COP")
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.ES)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="tenants")
    theme = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        # Los subdominios reservados se rechazan siempre, no solo en full_clean().
        validate_slug(self.slug)
        super().save(*args, **kwargs)


class Domain(BaseModel):
    class Kind(models.TextChoices):
        SUBDOMAIN = "subdomain"
        CUSTOM = "custom"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="domains")
    host = models.CharField(max_length=253, unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SUBDOMAIN)
    verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, default=_new_token)

    def __str__(self) -> str:
        return self.host

    def save(self, *args, **kwargs) -> None:
        self.host = self.host.strip().lower().rstrip(".")
        super().save(*args, **kwargs)


class TenantModule(BaseModel):
    """Módulo habilitado para un tenant. Configuración de plataforma: la gestiona el Super Admin."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="modules")
    module_key = models.CharField(max_length=50, choices=[(key, key) for key in MODULE_KEYS])
    enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "module_key"], name="uniq_tenant_module"),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id}:{self.module_key}={self.enabled}"


class TenantManager(models.Manager["TenantOwnedModel"]):
    """Filtra por el tenant activo. Sin tenant activo no devuelve nada (falla cerrado)."""

    def get_queryset(self) -> models.QuerySet:
        queryset = super().get_queryset().filter(deleted_at__isnull=True)
        tenant = get_current_tenant()
        if tenant is None:
            return queryset.none()
        return queryset.filter(tenant_id=tenant.pk)


class TenantOwnedModel(BaseModel):
    """Base de todo modelo de negocio. Cada tabla hija debe activar RLS en su migración
    (`apps.tenancy.rls.enable_rls`)."""

    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="+", editable=False)

    objects = TenantManager()
    # Sin filtro de tenant: solo Super Admin y tareas globales (dentro de `platform_context`).
    all_tenants = models.Manager()  # noqa: DJ012 (el manager por defecto debe declararse primero)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        current = get_current_tenant()
        if self.tenant_id is None:
            if current is None:
                raise ImproperlyConfigured(
                    f"No hay tenant activo para guardar {type(self).__name__}."
                )
            self.tenant = current
        elif current is not None and self.tenant_id != current.pk:
            raise ImproperlyConfigured("No se puede guardar un registro de otro tenant.")
        super().save(*args, **kwargs)
