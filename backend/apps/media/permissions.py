from rest_framework.permissions import BasePermission

from apps.accounts import permissions as perms


class CanUploadMedia(BasePermission):
    """Sube imágenes quien puede editar la empresa (logo) o el catálogo y el equipo (fotos)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and getattr(request, "tenant", None)):
            return False
        return perms.can(user.role, perms.COMPANY, "update") or perms.can(
            user.role, perms.STAFF_SERVICES, "update"
        )
