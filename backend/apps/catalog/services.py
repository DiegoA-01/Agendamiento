"""API pública de la app catalog para otras apps.

Búsquedas de lectura para `scheduling` (horarios, M4) y para el motor de disponibilidad y la
creación de citas (M5). Todas buscan dentro del tenant activo: un id de otro negocio, borrado o
inválido se trata como inexistente.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q

from .models import Professional, ProfessionalService, Resource, Service


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


def location_in_use(location_id) -> bool:
    """Si alguna ficha vigente (profesional o puesto) usa la sede: no se puede borrar."""
    return (
        Professional.objects.filter(location_id=location_id).exists()
        or Resource.objects.filter(location_id=location_id).exists()
    )


def get_resource(resource_id) -> Resource | None:
    if not _is_uuid(resource_id):
        return None
    return Resource.objects.filter(pk=resource_id).first()


def professional_for_user(user) -> Professional | None:
    """Ficha de profesional enlazada a la cuenta, o None si la cuenta no tiene una."""
    return Professional.objects.filter(user_id=user.pk).first()


# --- Motor de disponibilidad y citas (M5) -------------------------------------------------------


def get_bookable_services(service_ids: Iterable) -> list[Service] | None:
    """Servicios activos con esos ids, en el orden pedido (sin repetidos).

    None si la lista está vacía o si algún id no existe, está inactivo o es de otro negocio: el
    llamador responde 400/404 en vez de calcular con una parte de los servicios.
    """
    ids = list(dict.fromkeys(str(value) for value in service_ids))
    if not ids or not all(_is_uuid(value) for value in ids):
        return None
    found = {str(s.pk): s for s in Service.objects.filter(pk__in=ids, is_active=True)}
    if len(found) != len(ids):
        return None
    return [found[value] for value in ids]


def professionals_for_services(
    services: list[Service], *, online_only: bool = False
) -> list[Professional]:
    """Profesionales activos que ofrecen **todos** los servicios, por orden alfabético (spec §8.2).

    `online_only=True` deja solo a quienes aceptan reservas en línea (la reserva pública).
    """
    if not services:
        return []
    service_ids = [service.pk for service in services]
    offered = Count(
        "service_links",
        filter=Q(
            service_links__service_id__in=service_ids,
            service_links__deleted_at__isnull=True,
        ),
        distinct=True,
    )
    professionals = Professional.objects.filter(is_active=True)
    if online_only:
        professionals = professionals.filter(accepts_online_booking=True)
    return list(
        professionals.annotate(offered=offered)
        .filter(offered=len(service_ids))
        .order_by("display_name", "pk")
    )


def requires_resource(services: Iterable[Service]) -> bool:
    """Si la cita necesita un puesto libre además del profesional (spec §8.5)."""
    return any(service.requires_resource for service in services)


def active_resources(location_id=None) -> list[Resource]:
    """Puestos activos (de una sede, si se indica), por nombre."""
    resources = Resource.objects.filter(is_active=True)
    if location_id is not None:
        resources = resources.filter(location_id=location_id)
    return list(resources.order_by("name", "pk"))


@dataclass(frozen=True)
class QuotedItem:
    """Un servicio de la cita con lo que cobra, dura y comisiona este profesional."""

    service_id: uuid.UUID
    price: Decimal
    duration_min: int
    commission_pct: Decimal


@dataclass(frozen=True)
class Quote:
    """Lo que costaría y duraría una cita con un profesional. Se congela en `AppointmentItem`."""

    professional_id: uuid.UUID
    items: tuple[QuotedItem, ...]
    total_price: Decimal
    # Suma de las duraciones (con overrides) + el buffer del último servicio (spec §8.1).
    total_duration_min: int
    requires_resource: bool


def quote(professional: Professional, services: list[Service]) -> Quote | None:
    """Precio, duración y comisión de cada servicio para este profesional.

    Prioridad: el override de `ProfessionalService` y, si no hay, el valor del servicio (precio y
    duración) o el porcentaje por defecto del profesional (comisión). None si el profesional no
    ofrece alguno de los servicios.
    """
    if not services:
        return None
    links = {
        link.service_id: link
        for link in ProfessionalService.objects.filter(
            professional=professional, service__in=services
        )
    }
    if len(links) != len({service.pk for service in services}):
        return None

    items = []
    for service in services:
        link = links[service.pk]
        items.append(
            QuotedItem(
                service_id=service.pk,
                price=_money(_first(link.price_override, service.price)),
                duration_min=_first(link.duration_override_min, service.duration_min),
                commission_pct=_first(
                    link.commission_pct_override, professional.default_commission_pct
                ),
            )
        )
    return Quote(
        professional_id=professional.pk,
        items=tuple(items),
        total_price=_money(sum((item.price for item in items), Decimal("0"))),
        total_duration_min=sum(item.duration_min for item in items) + services[-1].buffer_min,
        requires_resource=requires_resource(services),
    )


def _first(override, default):
    return default if override is None else override


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
