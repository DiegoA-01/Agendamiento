"""API pública de la app catalog para otras apps.

Por ahora solo búsquedas de lectura que necesita `scheduling` (M4, frente A). Las funciones del
motor de disponibilidad (duraciones con overrides, profesionales por servicio) llegan en B4.1.
Todas buscan dentro del tenant activo: un id de otro negocio devuelve None.
"""

import uuid

from .models import Professional, Resource


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True


def get_professional(professional_id) -> Professional | None:
    if not _is_uuid(professional_id):
        return None
    return Professional.objects.filter(pk=professional_id).first()


def get_resource(resource_id) -> Resource | None:
    if not _is_uuid(resource_id):
        return None
    return Resource.objects.filter(pk=resource_id).first()


def professional_for_user(user) -> Professional | None:
    """Ficha de profesional enlazada a la cuenta, o None si la cuenta no tiene una."""
    return Professional.objects.filter(user_id=user.pk).first()
