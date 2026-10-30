"""Acciones del Super Admin. Cada una deja una entrada en el registro de auditoría.

Orquesta las demás apps solo por sus `services.py`: tenancy (negocio, dominios, planes), company
(datos de empresa) y accounts (propietario).
"""

import secrets
import uuid
from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.accounts import services as accounts
from apps.accounts.models import User
from apps.company import services as company
from apps.tenancy import services as tenancy
from config.api import ApiError

from .models import AuditLog


def _client_ip(request: HttpRequest) -> str | None:
    return request.META.get("REMOTE_ADDR") or None


def record(
    request: HttpRequest,
    action: str,
    entity: str,
    entity_id: Any,
    *,
    tenant=None,
    before: Any = None,
    after: Any = None,
) -> AuditLog:
    return AuditLog.objects.create(
        actor=request.user,
        tenant=tenant,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        before=before,
        after=after,
        ip=_client_ip(request),
    )


def list_audit_log(*, tenant_id: uuid.UUID | None = None, action: str = "") -> QuerySet[AuditLog]:
    queryset = AuditLog.objects.select_related("actor", "tenant")
    if tenant_id is not None:
        queryset = queryset.filter(tenant_id=tenant_id)
    if action:
        queryset = queryset.filter(action=action)
    return queryset


def tenant_snapshot(tenant) -> dict[str, Any]:
    """Foto de los datos del negocio para el registro de auditoría (sin secretos)."""
    return {
        "name": tenant.name,
        "slug": tenant.slug,
        "vertical": tenant.vertical,
        "timezone": tenant.timezone,
        "currency": tenant.currency,
        "language": tenant.language,
        "status": tenant.status,
        "plan": str(tenant.plan_id),
    }


def plan_snapshot(plan) -> dict[str, Any]:
    return {
        "name": plan.name,
        "modules": plan.modules,
        "max_professionals": plan.max_professionals,
        "max_locations": plan.max_locations,
    }


def _temporary_password() -> str:
    return secrets.token_urlsafe(12)


def create_tenant_with_owner(
    request: HttpRequest,
    *,
    name: str,
    slug: str,
    plan,
    owner_email: str,
    owner_name: str,
    vertical: str,
    timezone: str,
    currency: str,
    language: str,
) -> tuple[Any, User, str]:
    """Alta completa de un negocio: tenant + subdominio + módulos + empresa + propietario.

    Devuelve (tenant, propietario, contraseña temporal). La contraseña se muestra una sola vez y
    no se guarda en ningún registro: el propietario debe cambiarla en su primer ingreso.
    """
    password = _temporary_password()
    with transaction.atomic():
        tenant = tenancy.create_tenant(
            name=name,
            slug=slug,
            plan=plan,
            vertical=vertical,
            timezone=timezone,
            currency=currency,
            language=language,
        )
        company.create_company(tenant, trade_name=name)
        owner = accounts.create_tenant_user(
            tenant=tenant,
            email=owner_email,
            full_name=owner_name,
            role=User.Role.OWNER,
            password=password,
            must_change_password=True,
        )
        record(
            request,
            "tenant.create",
            "tenant",
            tenant.pk,
            tenant=tenant,
            after={**tenant_snapshot(tenant), "owner_email": owner.email},
        )
    return tenant, owner, password


def update_tenant(request: HttpRequest, tenant, **changes: Any):
    before = tenant_snapshot(tenant)
    tenant = tenancy.update_tenant(tenant, **changes)
    record(
        request,
        "tenant.update",
        "tenant",
        tenant.pk,
        tenant=tenant,
        before=before,
        after=tenant_snapshot(tenant),
    )
    return tenant


def set_status(request: HttpRequest, tenant, *, suspend: bool):
    before = tenant.status
    tenant = tenancy.suspend_tenant(tenant) if suspend else tenancy.activate_tenant(tenant)
    record(
        request,
        "tenant.suspend" if suspend else "tenant.activate",
        "tenant",
        tenant.pk,
        tenant=tenant,
        before={"status": before},
        after={"status": tenant.status},
    )
    return tenant


def delete_tenant(request: HttpRequest, tenant) -> None:
    snapshot = tenant_snapshot(tenant)
    tenancy.soft_delete_tenant(tenant)
    record(request, "tenant.delete", "tenant", tenant.pk, tenant=tenant, before=snapshot)


def set_theme(request: HttpRequest, tenant, theme: Any) -> dict[str, str]:
    before = tenant.theme
    new_theme = tenancy.set_theme(tenant, theme)
    record(
        request, "tenant.theme", "tenant", tenant.pk, tenant=tenant, before=before, after=new_theme
    )
    return new_theme


def set_modules(request: HttpRequest, tenant, modules: dict[str, bool]) -> set[str]:
    before = sorted(tenancy.enabled_module_keys(tenant))
    enabled = tenancy.set_modules(tenant, modules)
    record(
        request,
        "tenant.modules",
        "tenant",
        tenant.pk,
        tenant=tenant,
        before=before,
        after=sorted(enabled),
    )
    return enabled


def add_domain(request: HttpRequest, tenant, host: str):
    domain = tenancy.add_custom_domain(tenant, host)
    record(request, "domain.add", "domain", domain.pk, tenant=tenant, after={"host": domain.host})
    return domain


def verify_domain(request: HttpRequest, tenant, domain) -> dict[str, bool]:
    result = tenancy.verify_domain(domain)
    record(
        request,
        "domain.verify",
        "domain",
        domain.pk,
        tenant=tenant,
        after={"host": domain.host, **result},
    )
    return result


def remove_domain(request: HttpRequest, tenant, domain) -> None:
    host = domain.host
    domain_id = domain.pk
    tenancy.remove_domain(domain)
    record(request, "domain.remove", "domain", domain_id, tenant=tenant, before={"host": host})


def create_plan(request: HttpRequest, **data: Any):
    plan = tenancy.create_plan(**data)
    record(request, "plan.create", "plan", plan.pk, after=plan_snapshot(plan))
    return plan


def update_plan(request: HttpRequest, plan, *, apply_to_tenants: bool = False, **changes: Any):
    before = plan_snapshot(plan)
    plan = tenancy.update_plan(plan, apply_to_tenants=apply_to_tenants, **changes)
    record(
        request,
        "plan.update",
        "plan",
        plan.pk,
        before=before,
        after={**plan_snapshot(plan), "apply_to_tenants": apply_to_tenants},
    )
    return plan


def delete_plan(request: HttpRequest, plan) -> None:
    snapshot = plan_snapshot(plan)
    plan_id = plan.pk
    tenancy.delete_plan(plan)
    record(request, "plan.delete", "plan", plan_id, before=snapshot)


def not_found(what: str = "Recurso") -> ApiError:
    return ApiError("not_found", f"{what} no encontrado.", 404)
