"""API pública de la app scheduling: horarios de trabajo y bloqueos de agenda (M4).

M5 agrega aquí el motor de disponibilidad (spec §8).

Alcance por rol (spec §5): owner, admin y recepción gestionan los horarios y bloqueos de todos;
un profesional solo los suyos. Lo ajeno se responde como si no existiera (404, no 403), para no
revelar qué ids hay.
"""

import datetime as dt
import uuid
from collections.abc import Iterable

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts import permissions as perms
from apps.booking import services as booking
from apps.catalog import services as catalog
from config.api import ApiError

from .models import TimeBlock, WorkingHours

# Tope de franjas por semana en un PUT: sobra para cualquier horario real (7 días con descansos)
# y evita guardar listas enormes.
MAX_WEEKLY_INTERVALS = 50


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True


def not_found(entity: str) -> ApiError:
    return ApiError("not_found", f"{entity} no encontrado.", 404)


def _scope(user, action: str) -> str:
    scope = perms.scope_for(user.role, perms.SCHEDULES, action)
    if scope is None:
        raise ApiError("permission_denied", "No tienes permiso para esta acción.", 403)
    return scope


def _own_professional_id(user):
    own = catalog.professional_for_user(user)
    return own.pk if own is not None else None


def professional_for(user, professional_id, action: str = "view"):
    """Profesional del tenant activo que `user` puede gestionar, o 404."""
    scope = _scope(user, action)
    professional = catalog.get_professional(professional_id)
    if professional is None or (
        scope == perms.OWN and professional.pk != _own_professional_id(user)
    ):
        raise not_found("Profesional")
    return professional


# --- Horarios de trabajo -------------------------------------------------------------------------


def get_working_hours(professional) -> QuerySet[WorkingHours]:
    return WorkingHours.objects.filter(professional=professional).order_by("weekday", "start_time")


def _check_no_overlap(intervals: list[dict]) -> None:
    """Dos franjas del mismo día no pueden traslaparse (sí tocarse: 9-12 y 12-18 vale)."""
    by_day: dict[int, list[dict]] = {}
    for interval in intervals:
        by_day.setdefault(interval["weekday"], []).append(interval)
    for weekday, day in by_day.items():
        day.sort(key=lambda i: i["start_time"])
        for previous, current in zip(day, day[1:], strict=False):
            if current["start_time"] < previous["end_time"]:
                raise ApiError(
                    "overlapping_hours",
                    "Hay franjas que se traslapan el mismo día.",
                    400,
                    {"weekday": [weekday]},
                )


def replace_working_hours(professional, intervals: Iterable[dict]) -> QuerySet[WorkingHours]:
    """Reemplaza la semana completa del profesional. Una lista vacía lo deja sin horario."""
    intervals = list(intervals)
    if len(intervals) > MAX_WEEKLY_INTERVALS:
        raise ApiError(
            "too_many_intervals", f"Máximo {MAX_WEEKLY_INTERVALS} franjas por semana.", 400
        )
    _check_no_overlap(intervals)
    with transaction.atomic():
        get_working_hours(professional).update(deleted_at=timezone.now())
        for interval in intervals:
            WorkingHours.objects.create(professional=professional, **interval)
    return get_working_hours(professional)


# --- Bloqueos ------------------------------------------------------------------------------------


def list_time_blocks(
    user,
    *,
    professional_id=None,
    resource_id=None,
    start_at: dt.datetime | None = None,
    end_at: dt.datetime | None = None,
) -> QuerySet[TimeBlock]:
    """Bloqueos visibles para `user`, opcionalmente filtrados por dueño y por rango de fechas."""
    blocks = TimeBlock.objects.all()
    if _scope(user, "view") == perms.OWN:
        blocks = blocks.filter(professional_id=_own_professional_id(user))
    if professional_id is not None:
        blocks = blocks.filter(professional_id=professional_id)
    if resource_id is not None:
        blocks = blocks.filter(resource_id=resource_id)
    if start_at is not None:
        blocks = blocks.filter(end_at__gt=start_at)
    if end_at is not None:
        blocks = blocks.filter(start_at__lt=end_at)
    return blocks.order_by("start_at")


def get_time_block(user, block_id, action: str = "view") -> TimeBlock:
    scope = _scope(user, action)
    block = TimeBlock.objects.filter(pk=block_id).first() if _is_uuid(block_id) else None
    if block is None or (
        scope == perms.OWN and block.professional_id != _own_professional_id(user)
    ):
        raise not_found("Bloqueo")
    return block


def _check_no_appointments(block: TimeBlock) -> None:
    """Spec §6: un bloqueo que choca con citas activas se rechaza con 409 y la lista de citas."""
    conflicts = booking.overlapping_appointments(
        block.start_at,
        block.end_at,
        professional_id=block.professional_id,
        resource_id=block.resource_id,
    )
    if conflicts.exists():
        raise ApiError(
            "time_block_conflict",
            "El bloqueo choca con citas existentes.",
            409,
            {
                "appointments": [
                    {
                        "id": str(appointment.pk),
                        "start_at": timezone.localtime(appointment.start_at).isoformat(),
                        "end_at": timezone.localtime(appointment.end_at).isoformat(),
                        "status": appointment.status,
                    }
                    for appointment in conflicts
                ]
            },
        )


def create_time_block(
    user,
    *,
    start_at: dt.datetime,
    end_at: dt.datetime,
    reason: str = "",
    professional_id=None,
    resource_id=None,
) -> TimeBlock:
    """Bloquea la agenda de un profesional o de un puesto (exactamente uno de los dos)."""
    scope = _scope(user, "create")
    if (professional_id is None) == (resource_id is None):
        raise ApiError(
            "validation_error",
            "Indica un profesional o un puesto, no ambos.",
            400,
            {"non_field_errors": ["Indica professional_id o resource_id."]},
        )
    block = TimeBlock(start_at=start_at, end_at=end_at, reason=reason)
    if professional_id is not None:
        block.professional = professional_for(user, professional_id, "create")
    else:
        # Los puestos son del negocio, no de un profesional: quien solo gestiona lo suyo no los
        # bloquea.
        if scope == perms.OWN:
            raise ApiError("permission_denied", "No puedes bloquear puestos.", 403)
        block.resource = catalog.get_resource(resource_id)
        if block.resource is None:
            raise not_found("Puesto")
    _check_no_appointments(block)
    block.save()
    return block


def update_time_block(user, block_id, **changes) -> TimeBlock:
    """Cambia fechas o motivo. El dueño (profesional o puesto) no se cambia: se crea otro."""
    block = get_time_block(user, block_id, "update")
    for field in ("start_at", "end_at", "reason"):
        if field in changes:
            setattr(block, field, changes[field])
    if block.start_at >= block.end_at:
        raise ApiError(
            "validation_error",
            "Datos inválidos.",
            400,
            {"end_at": ["Debe ser posterior al inicio."]},
        )
    _check_no_appointments(block)
    block.save()
    return block


def delete_time_block(user, block_id) -> None:
    block = get_time_block(user, block_id, "delete")
    block.deleted_at = timezone.now()
    block.save(update_fields=["deleted_at", "updated_at"])
