"""API pública de la app tenancy: las demás apps solo importan desde aquí."""

import re
import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import ProtectedError, Q, QuerySet
from django.utils import timezone

from config.api import ApiError

from .constants import MODULE_KEYS
from .context import get_current_tenant, platform_context, tenant_context
from .dns import DnsLookupError, get_resolver
from .models import Domain, Plan, Tenant, TenantModule
from .theme import DEFAULT_THEME, validate_theme

__all__ = [
    "activate_tenant",
    "add_custom_domain",
    "admin_host",
    "create_plan",
    "create_tenant",
    "delete_plan",
    "dns_instructions",
    "enabled_module_keys",
    "ensure_subdomain",
    "get_current_tenant",
    "get_domain",
    "get_plan",
    "get_tenant",
    "get_tenant_by_slug",
    "is_module_enabled",
    "list_domains",
    "list_plans",
    "list_tenants",
    "platform_context",
    "remove_domain",
    "resolve_domain",
    "set_modules",
    "set_theme",
    "soft_delete_tenant",
    "subdomain_host",
    "suspend_tenant",
    "sync_modules_from_plan",
    "tenant_context",
    "update_plan",
    "update_tenant",
    "verify_domain",
]

_HOST_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
TENANT_EDITABLE_FIELDS = ("name", "vertical", "timezone", "currency", "language", "plan")
CHALLENGE_PREFIX = "_agenda-challenge"


def _validation_error(exc: ValidationError) -> ApiError:
    fields = exc.message_dict if hasattr(exc, "error_dict") else {"non_field_errors": exc.messages}
    return ApiError("validation_error", "Datos inválidos.", 400, fields)


def _validated(instance: models.Model) -> None:
    try:
        instance.full_clean()
    except ValidationError as exc:
        raise _validation_error(exc) from exc


# --- Hosts -------------------------------------------------------------------------------------


def subdomain_host(slug: str) -> str:
    return f"{slug}.{settings.BASE_DOMAIN}"


def admin_host() -> str:
    return f"admin.{settings.BASE_DOMAIN}"


def resolve_domain(host: str) -> Domain | None:
    """Dominio verificado y vigente que corresponde al host, con su tenant."""
    return (
        Domain.objects.select_related("tenant")
        .filter(host=host, verified=True, deleted_at__isnull=True, tenant__deleted_at__isnull=True)
        .first()
    )


def ensure_subdomain(tenant: Tenant) -> Domain:
    """Crea (verificado) el subdominio `<slug>.<BASE_DOMAIN>` del tenant si no existe."""
    domain, _ = Domain.objects.get_or_create(
        host=subdomain_host(tenant.slug),
        defaults={"tenant": tenant, "kind": Domain.Kind.SUBDOMAIN, "verified": True},
    )
    return domain


# --- Módulos -----------------------------------------------------------------------------------


def sync_modules_from_plan(tenant: Tenant) -> None:
    """Alinea los `TenantModule` del tenant con los módulos de su plan."""
    included = set(tenant.plan.modules)
    for key in MODULE_KEYS:
        TenantModule.objects.update_or_create(
            tenant=tenant, module_key=key, defaults={"enabled": key in included}
        )


def enabled_module_keys(tenant: Tenant) -> set[str]:
    return set(
        TenantModule.objects.filter(
            tenant=tenant, enabled=True, deleted_at__isnull=True
        ).values_list("module_key", flat=True)
    )


def is_module_enabled(tenant: Tenant | None, module_key: str) -> bool:
    return tenant is not None and module_key in enabled_module_keys(tenant)


def set_modules(tenant: Tenant, modules: dict[str, bool]) -> set[str]:
    """Activa o desactiva módulos puntuales (por encima de lo que da el plan)."""
    unknown = sorted(set(modules) - set(MODULE_KEYS))
    if unknown:
        raise ApiError(
            "validation_error",
            "Módulos desconocidos.",
            400,
            {"modules": [f"Desconocido: {key}" for key in unknown]},
        )
    for key, enabled in modules.items():
        TenantModule.objects.update_or_create(
            tenant=tenant, module_key=key, defaults={"enabled": bool(enabled)}
        )
    return enabled_module_keys(tenant)


# --- Negocios ----------------------------------------------------------------------------------


def list_tenants(*, search: str = "", status: str = "") -> QuerySet[Tenant]:
    queryset = Tenant.objects.filter(deleted_at__isnull=True).select_related("plan")
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(slug__icontains=search))
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def get_tenant(tenant_id: uuid.UUID) -> Tenant | None:
    return (
        Tenant.objects.select_related("plan").filter(pk=tenant_id, deleted_at__isnull=True).first()
    )


def get_tenant_by_slug(slug: str) -> Tenant | None:
    return (
        Tenant.objects.select_related("plan")
        .filter(slug=slug.strip().lower(), deleted_at__isnull=True)
        .first()
    )


def create_tenant(
    *,
    name: str,
    slug: str,
    plan: Plan,
    vertical: str = Tenant.Vertical.BARBERSHOP,
    timezone: str = "America/Bogota",
    currency: str = "COP",
    language: str = Tenant.Language.ES,
) -> Tenant:
    """Crea el negocio con su subdominio verificado, el tema por defecto y los módulos del plan."""
    tenant = Tenant(
        name=name.strip(),
        slug=slug.strip().lower(),
        plan=plan,
        vertical=vertical,
        timezone=timezone,
        currency=currency.upper(),
        language=language,
        theme=dict(DEFAULT_THEME),
    )
    _validated(tenant)
    with transaction.atomic():
        tenant.save()
        ensure_subdomain(tenant)
        sync_modules_from_plan(tenant)
    return tenant


def update_tenant(tenant: Tenant, **changes: Any) -> Tenant:
    """Edita datos del negocio. El slug no cambia (es su subdominio). Cambiar de plan reinicia
    los módulos a los del plan nuevo."""
    unknown = set(changes) - set(TENANT_EDITABLE_FIELDS)
    if unknown:
        raise ApiError(
            "validation_error", "Campos no editables.", 400, {k: ["No editable"] for k in unknown}
        )
    plan_changed = "plan" in changes and changes["plan"].pk != tenant.plan_id
    for field, value in changes.items():
        setattr(tenant, field, value)
    if "currency" in changes:
        tenant.currency = tenant.currency.upper()
    _validated(tenant)
    with transaction.atomic():
        tenant.save()
        if plan_changed:
            sync_modules_from_plan(tenant)
    return tenant


def suspend_tenant(tenant: Tenant) -> Tenant:
    tenant.status = Tenant.Status.SUSPENDED
    tenant.save(update_fields=["status", "updated_at"])
    return tenant


def activate_tenant(tenant: Tenant) -> Tenant:
    tenant.status = Tenant.Status.ACTIVE
    tenant.save(update_fields=["status", "updated_at"])
    return tenant


def soft_delete_tenant(tenant: Tenant) -> None:
    """Borrado lógico: el negocio deja de resolver por host. Los datos no se eliminan."""
    tenant.deleted_at = timezone.now()
    tenant.save(update_fields=["deleted_at", "updated_at"])


def set_theme(tenant: Tenant, theme: Any) -> dict[str, str]:
    tenant.theme = validate_theme(theme)
    tenant.save(update_fields=["theme", "updated_at"])
    return tenant.theme


# --- Planes ------------------------------------------------------------------------------------


def list_plans() -> QuerySet[Plan]:
    return Plan.objects.filter(deleted_at__isnull=True).order_by("name")


def get_plan(plan_id: uuid.UUID) -> Plan | None:
    return Plan.objects.filter(pk=plan_id, deleted_at__isnull=True).first()


def create_plan(
    *, name: str, modules: list[str], max_professionals: int, max_locations: int
) -> Plan:
    plan = Plan(
        name=name.strip(),
        modules=list(modules),
        max_professionals=max_professionals,
        max_locations=max_locations,
    )
    _validated(plan)
    plan.save()
    return plan


def update_plan(plan: Plan, *, apply_to_tenants: bool = False, **changes: Any) -> Plan:
    """Edita un plan. Los negocios que ya lo usan NO cambian de módulos salvo que se pida
    `apply_to_tenants` (eso sobrescribe los ajustes manuales de módulos de cada negocio)."""
    for field, value in changes.items():
        setattr(plan, field, list(value) if field == "modules" else value)
    _validated(plan)
    with transaction.atomic():
        plan.save()
        if apply_to_tenants:
            for tenant in plan.tenants.filter(deleted_at__isnull=True):
                tenant.plan = plan
                sync_modules_from_plan(tenant)
    return plan


def delete_plan(plan: Plan) -> None:
    if plan.tenants.filter(deleted_at__isnull=True).exists():
        raise ApiError("plan_in_use", "Hay negocios usando este plan.", 409)
    try:
        plan.delete()  # sin ningún negocio: se libera el nombre
    except ProtectedError:
        plan.deleted_at = timezone.now()  # solo lo usaron negocios ya borrados
        plan.save(update_fields=["deleted_at", "updated_at"])


# --- Dominios propios --------------------------------------------------------------------------


def list_domains(tenant: Tenant) -> QuerySet[Domain]:
    return Domain.objects.filter(tenant=tenant, deleted_at__isnull=True).order_by("created_at")


def get_domain(tenant: Tenant, domain_id: uuid.UUID) -> Domain | None:
    return Domain.objects.filter(tenant=tenant, pk=domain_id, deleted_at__isnull=True).first()


def add_custom_domain(tenant: Tenant, host: str) -> Domain:
    host = host.strip().lower().rstrip(".")
    base = settings.BASE_DOMAIN
    # Primero lo reservado: así "localhost" (sin punto) también se explica como de la plataforma.
    if host == base or host.endswith(f".{base}"):
        raise ApiError(
            "reserved_host",
            "Los subdominios de la plataforma se crean solos.",
            400,
            {"host": ["Usa un dominio propio del negocio."]},
        )
    if not _HOST_RE.match(host):
        raise ApiError(
            "invalid_host", "Dominio inválido.", 400, {"host": ["Ej.: www.minegocio.com"]}
        )
    if Domain.objects.filter(host=host).exists():
        raise ApiError("host_taken", "Ese dominio ya está registrado.", 409, {"host": ["En uso."]})
    return Domain.objects.create(tenant=tenant, host=host, kind=Domain.Kind.CUSTOM, verified=False)


def remove_domain(domain: Domain) -> None:
    if domain.kind == Domain.Kind.SUBDOMAIN:
        raise ApiError("cannot_delete_subdomain", "El subdominio base no se puede quitar.", 400)
    domain.delete()


def dns_instructions(domain: Domain) -> dict[str, dict[str, str]]:
    """Qué registros debe crear el cliente en su proveedor de DNS."""
    return {
        "txt": {"name": f"{CHALLENGE_PREFIX}.{domain.host}", "value": domain.verification_token},
        "cname": {"name": domain.host, "target": subdomain_host(domain.tenant.slug)},
    }


def verify_domain(domain: Domain) -> dict[str, bool]:
    """Verifica la propiedad del dominio por el registro TXT. El CNAME se informa, no se exige."""
    instructions = dns_instructions(domain)
    resolver = get_resolver()
    try:
        txt_ok = domain.verification_token in resolver.txt(instructions["txt"]["name"])
    except DnsLookupError as exc:
        raise ApiError("dns_lookup_failed", "No se pudo consultar el DNS. Reintenta.", 503) from exc
    try:
        cname_ok = instructions["cname"]["target"] in resolver.cname(domain.host)
    except DnsLookupError:
        cname_ok = False
    if txt_ok and not domain.verified:
        domain.verified = True
        domain.save(update_fields=["verified", "updated_at"])
    return {"verified": domain.verified, "txt_ok": txt_ok, "cname_ok": cname_ok}
