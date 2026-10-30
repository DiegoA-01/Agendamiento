"""Matriz de permisos por rol (spec §5) como datos, más la clase DRF que la aplica.

Cada celda dice qué acciones puede hacer un rol sobre un recurso y con qué alcance:
`all` = todos los registros del tenant, `own` = solo los suyos (p. ej. un profesional ve solo sus
citas). El tema solo lo edita el Super Admin, por eso cae bajo `PLATFORM`.
"""

from dataclasses import dataclass

from rest_framework.permissions import BasePermission

from .models import User

ALL = "all"
OWN = "own"

# Recursos
COMPANY = "company"  # datos de empresa y términos
STAFF_SERVICES = "staff_services"  # empleados y servicios
SCHEDULES = "schedules"  # horarios y bloqueos
APPOINTMENTS = "appointments"
COMMISSIONS = "commissions"  # comisiones y reportes
PLAN_MODULES = "plan_modules"
PLATFORM = "platform"  # empresas, planes, tema, dominios, auditoría

CRUD = ("view", "create", "update", "delete")
APPOINTMENT_ACTIONS = (*CRUD, "confirm", "start", "complete", "cancel", "no_show", "reschedule")


@dataclass(frozen=True)
class Grant:
    scope: str
    actions: frozenset[str]


def grant(scope: str, *actions: str) -> Grant:
    return Grant(scope, frozenset(actions))


R = User.Role

MATRIX: dict[str, dict[str, Grant]] = {
    COMPANY: {
        R.OWNER: grant(ALL, "view", "update"),
        R.ADMIN: grant(ALL, "view"),
    },
    STAFF_SERVICES: {
        R.OWNER: grant(ALL, *CRUD),
        R.ADMIN: grant(ALL, *CRUD),
        R.RECEPTIONIST: grant(ALL, "view"),
        R.PROFESSIONAL: grant(OWN, "view"),
    },
    SCHEDULES: {
        R.OWNER: grant(ALL, *CRUD),
        R.ADMIN: grant(ALL, *CRUD),
        R.RECEPTIONIST: grant(ALL, *CRUD),
        R.PROFESSIONAL: grant(OWN, *CRUD),
    },
    APPOINTMENTS: {
        R.OWNER: grant(ALL, *APPOINTMENT_ACTIONS),
        R.ADMIN: grant(ALL, *APPOINTMENT_ACTIONS),
        R.RECEPTIONIST: grant(ALL, *APPOINTMENT_ACTIONS),
        R.PROFESSIONAL: grant(OWN, "view", "complete", "no_show"),
    },
    COMMISSIONS: {
        R.OWNER: grant(ALL, "view"),
        R.ADMIN: grant(ALL, "view"),
        R.PROFESSIONAL: grant(OWN, "view"),
    },
    PLAN_MODULES: {
        R.OWNER: grant(ALL, "view"),
    },
    PLATFORM: {
        R.SUPERADMIN: grant(ALL, *CRUD),
    },
}


def get_grant(role: str, resource: str) -> Grant | None:
    return MATRIX.get(resource, {}).get(role)


def can(role: str, resource: str, action: str) -> bool:
    found = get_grant(role, resource)
    return found is not None and action in found.actions


def scope_for(role: str, resource: str, action: str) -> str | None:
    """`all`, `own` o None si no tiene permiso. Las vistas lo usan para filtrar los registros."""
    found = get_grant(role, resource)
    return found.scope if found is not None and action in found.actions else None


def permission_for(resource: str, action: str) -> type[BasePermission]:
    """Clase de permiso DRF: `permission_classes = [permission_for(APPOINTMENTS, "view")]`."""

    class RolePermission(BasePermission):
        def has_permission(self, request, view) -> bool:
            user = request.user
            return bool(user and user.is_authenticated and can(user.role, resource, action))

    RolePermission.__name__ = f"Can_{action}_{resource}"
    return RolePermission
