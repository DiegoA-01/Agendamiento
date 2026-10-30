"""API pública de la app tenancy: las demás apps solo importan desde aquí."""

from django.conf import settings

from .constants import MODULE_KEYS
from .context import get_current_tenant, platform_context, tenant_context
from .models import Domain, Tenant, TenantModule

__all__ = [
    "enabled_module_keys",
    "ensure_subdomain",
    "get_current_tenant",
    "is_module_enabled",
    "platform_context",
    "resolve_domain",
    "subdomain_host",
    "sync_modules_from_plan",
    "tenant_context",
]


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
