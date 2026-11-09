"""Comisiones (spec §11): se registran al completar una cita y no cambian nunca.

API pública de la app. `booking` llama a `record_for_appointment` dentro de la misma transacción
que pasa la cita a `completed`; `reports` lee con `entries_for`.
"""

import datetime as dt
import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts import permissions as perms
from apps.catalog import services as catalog
from config.api import ApiError

from .models import CommissionEntry

CENT = Decimal("0.01")


def split(base: Decimal, pct: Decimal) -> tuple[Decimal, Decimal]:
    """(comisión, negocio) de un valor. La comisión se redondea al centavo hacia arriba en la
    mitad (0,005 → 0,01) y el negocio es el resto, así las dos partes siempre suman `base`."""
    commission = (base * pct / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
    return commission, base - commission


def record_for_appointment(appointment) -> list[CommissionEntry]:
    """Una entrada por cada servicio de la cita, con el porcentaje congelado al reservar.

    Idempotente: si la cita ya tiene sus entradas, las devuelve sin crear otras.
    """
    existing = list(CommissionEntry.objects.filter(appointment=appointment, kind="entry"))
    if existing:
        return existing
    entries = []
    for item in appointment.items.all():
        commission, business = split(item.price_charged, item.commission_pct_snapshot)
        entries.append(
            CommissionEntry.objects.create(
                kind=CommissionEntry.Kind.ENTRY,
                appointment=appointment,
                appointment_item=item,
                professional_id=item.professional_id,
                service_id=item.service_id,
                appointment_start_at=appointment.start_at,
                base_amount=item.price_charged,
                pct=item.commission_pct_snapshot,
                commission_amount=commission,
                business_amount=business,
            )
        )
    return entries


@transaction.atomic
def create_adjustment(
    entry: CommissionEntry,
    *,
    base_amount: Decimal,
    commission_amount: Decimal,
    reason: str,
    created_by=None,
) -> CommissionEntry:
    """Corrige una comisión sin tocarla: guarda la diferencia como otra fila.

    `base_amount` y `commission_amount` son los valores corregidos del servicio (lo que debió
    ser); el ajuste lleva la diferencia con lo ya registrado (entrada más ajustes previos).
    """
    if entry.kind != CommissionEntry.Kind.ENTRY:
        raise ApiError("invalid_adjustment", "Solo se ajusta la entrada original.", 400)
    if not reason.strip():
        raise ApiError("invalid_adjustment", "El ajuste necesita un motivo.", 400, {"reason": []})
    if base_amount < 0 or not (0 <= commission_amount <= base_amount):
        raise ApiError(
            "invalid_adjustment",
            "La comisión debe estar entre 0 y el valor del servicio.",
            400,
        )
    rows = [entry, *entry.adjustments.all()]
    current_base = sum((row.base_amount for row in rows), Decimal(0))
    current_commission = sum((row.commission_amount for row in rows), Decimal(0))
    delta_base = base_amount - current_base
    delta_commission = commission_amount - current_commission
    if delta_base == 0 and delta_commission == 0:
        raise ApiError("invalid_adjustment", "El ajuste no cambia nada.", 400)
    pct = (commission_amount * 100 / base_amount).quantize(CENT) if base_amount else Decimal(0)
    return CommissionEntry.objects.create(
        kind=CommissionEntry.Kind.ADJUSTMENT,
        adjusts=entry,
        appointment_id=entry.appointment_id,
        appointment_item_id=entry.appointment_item_id,
        professional_id=entry.professional_id,
        service_id=entry.service_id,
        appointment_start_at=entry.appointment_start_at,
        base_amount=delta_base,
        pct=min(pct, Decimal(100)),
        commission_amount=delta_commission,
        business_amount=delta_base - delta_commission,
        reason=reason.strip(),
        created_by=created_by,
    )


# --- Lectura -----------------------------------------------------------------------------------


def own_professional_id(user):
    """Id de la ficha del profesional si solo puede ver lo suyo; None si ve todo el negocio.

    403 si su rol no ve comisiones ni reportes (spec §5). Sin ficha enlazada devuelve un id que
    no existe, así no ve ninguna fila en vez de ver todas.
    """
    scope = perms.scope_for(user.role, perms.COMMISSIONS, "view")
    if scope is None:
        raise ApiError("permission_denied", "No tienes permiso para esta acción.", 403)
    if scope == perms.ALL:
        return None
    own = catalog.professional_for_user(user)
    return own.pk if own is not None else uuid.UUID(int=0)


def require_adjust(user) -> None:
    """403 si el rol no puede corregir comisiones (solo el dueño)."""
    if not perms.can(user.role, perms.COMMISSIONS, "adjust"):
        raise ApiError("permission_denied", "No tienes permiso para esta acción.", 403)


def get_entry(user, entry_id) -> CommissionEntry:
    """La comisión, o 404 si no existe o es de otro profesional (404, no 403: spec §5)."""
    try:
        pk = uuid.UUID(str(entry_id))
    except ValueError:
        pk = None
    entry = entries_for(user).filter(pk=pk).first() if pk else None
    if entry is None:
        raise ApiError("not_found", "Comisión no encontrada.", 404)
    return entry


def local_range(start: dt.date, end: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """`[inicio del día start, inicio del día siguiente a end)` en la zona horaria activa."""
    tz = timezone.get_current_timezone()
    return (
        dt.datetime.combine(start, dt.time.min, tzinfo=tz),
        dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=tz),
    )


def entries_for(
    user,
    *,
    start_at: dt.datetime | None = None,
    end_at: dt.datetime | None = None,
    professional_id=None,
    service_id=None,
    category_id=None,
    kind: str | None = None,
) -> QuerySet[CommissionEntry]:
    """Comisiones visibles para `user`, filtradas por la fecha de la cita (`[start_at, end_at)`).

    Un profesional solo ve las suyas aunque pida las de otro (spec §11).
    """
    entries = CommissionEntry.objects.select_related("professional", "service", "appointment")
    own = own_professional_id(user)
    if own is not None:
        entries = entries.filter(professional_id=own)
    if professional_id is not None:
        entries = entries.filter(professional_id=professional_id)
    if service_id is not None:
        entries = entries.filter(service_id=service_id)
    if category_id is not None:
        entries = entries.filter(service__category_id=category_id)
    if start_at is not None:
        entries = entries.filter(appointment_start_at__gte=start_at)
    if end_at is not None:
        entries = entries.filter(appointment_start_at__lt=end_at)
    if kind:
        entries = entries.filter(kind=kind)
    return entries
