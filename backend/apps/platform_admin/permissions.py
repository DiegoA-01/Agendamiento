from rest_framework.permissions import BasePermission

from apps.accounts.permissions import PLATFORM, permission_for

_ACTION_BY_METHOD = {
    "GET": "view",
    "HEAD": "view",
    "OPTIONS": "view",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


class IsPlatformHost(BasePermission):
    """La API del Super Admin solo responde en el host `admin.`, nunca en el de un negocio."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user.is_authenticated and request.is_platform_admin)


def platform_permissions(method: str) -> list[BasePermission]:
    action = _ACTION_BY_METHOD.get(method, "view")
    return [IsPlatformHost(), permission_for(PLATFORM, action)()]
