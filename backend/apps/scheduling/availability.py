"""Motor de disponibilidad (spec §8).

Para cada profesional candidato, el tiempo libre de un día es: sus franjas de `WorkingHours` (en
la zona horaria del negocio) menos sus bloqueos menos sus citas activas. Dentro de ese tiempo se
ofrecen inicios cada `slot_step_min` donde cabe la duración total de los servicios; si algún
servicio exige puesto, además debe quedar un puesto libre de la sede del profesional.

El tiempo libre de un profesional en un día (lo único caro de calcular) se guarda en caché por
(negocio, versión, profesional, fecha). Cualquier cambio de agenda del negocio sube la versión con
`invalidate`, así no hay que adivinar qué claves borrar.
"""

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.utils import timezone

from apps.booking import services as booking
from apps.catalog import services as catalog
from config.api import ApiError

from .models import TimeBlock, WorkingHours

Interval = tuple[dt.datetime, dt.datetime]

CACHE_SECONDS = 60 * 60
# Franjas del día en hora local (spec §8.8).
AFTERNOON_FROM = dt.time(12, 0)
EVENING_FROM = dt.time(18, 0)


@dataclass(frozen=True)
class Slot:
    start: dt.datetime
    end: dt.datetime
    # Profesionales libres en ese inicio, en orden alfabético. Con "cualquiera" el cliente no los
    # ve: el profesional se asigna al confirmar (spec §8.7).
    professional_ids: tuple = field(default=())

    @property
    def period(self) -> str:
        local = self.start.timetz()
        if local < AFTERNOON_FROM:
            return "morning"
        return "afternoon" if local < EVENING_FROM else "evening"


# --- Caché --------------------------------------------------------------------------------------


def _version_key(tenant_id) -> str:
    return f"availability:version:{tenant_id}"


def invalidate(tenant_id) -> None:
    """Descarta todo el tiempo libre en caché del negocio. Se llama al cambiar citas, horarios o
    bloqueos."""
    key = _version_key(tenant_id)
    if not cache.add(key, 1, timeout=None):
        try:
            cache.incr(key)
        except ValueError:  # la clave expiró justo entre `add` e `incr`
            cache.set(key, 1, timeout=None)


def _free_key(tenant_id, professional_id, day: dt.date) -> str:
    version = cache.get(_version_key(tenant_id), 0)
    return f"availability:free:{tenant_id}:{version}:{professional_id}:{day.isoformat()}"


# --- Intervalos ---------------------------------------------------------------------------------


def _subtract(free: list[Interval], busy: list[Interval]) -> list[Interval]:
    """Resta intervalos ocupados `[inicio, fin)` a intervalos libres."""
    result = []
    for start, end in free:
        pieces = [(start, end)]
        for busy_start, busy_end in busy:
            next_pieces = []
            for piece_start, piece_end in pieces:
                if busy_end <= piece_start or busy_start >= piece_end:
                    next_pieces.append((piece_start, piece_end))
                    continue
                if piece_start < busy_start:
                    next_pieces.append((piece_start, busy_start))
                if busy_end < piece_end:
                    next_pieces.append((busy_end, piece_end))
            pieces = next_pieces
        result.extend(pieces)
    return result


def _day_bounds(day: dt.date, tz: ZoneInfo) -> Interval:
    start = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
    return start, dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min, tzinfo=tz)


def _working_intervals(professional, day: dt.date, tz: ZoneInfo) -> list[Interval]:
    rows = WorkingHours.objects.filter(professional=professional, weekday=day.weekday())
    return [
        (
            dt.datetime.combine(day, row.start_time, tzinfo=tz),
            dt.datetime.combine(day, row.end_time, tzinfo=tz),
        )
        for row in rows.order_by("start_time")
    ]


def _busy_intervals(day_start, day_end, *, professional_id=None, resource_id=None):
    blocks = TimeBlock.objects.filter(start_at__lt=day_end, end_at__gt=day_start)
    if professional_id is not None:
        blocks = blocks.filter(professional_id=professional_id)
    if resource_id is not None:
        blocks = blocks.filter(resource_id=resource_id)
    appointments = booking.overlapping_appointments(
        day_start, day_end, professional_id=professional_id, resource_id=resource_id
    )
    return [(b.start_at, b.end_at) for b in blocks] + [(a.start_at, a.end_at) for a in appointments]


def free_intervals(tenant, professional, day: dt.date, *, use_cache: bool = True):
    """Tiempo libre del profesional ese día: horario menos bloqueos menos citas activas."""
    key = _free_key(tenant.pk, professional.pk, day)
    if use_cache:
        cached = cache.get(key)
        if cached is not None:
            return [(dt.datetime.fromisoformat(a), dt.datetime.fromisoformat(b)) for a, b in cached]

    tz = ZoneInfo(tenant.timezone)
    day_start, day_end = _day_bounds(day, tz)
    free = _subtract(
        _working_intervals(professional, day, tz),
        _busy_intervals(day_start, day_end, professional_id=professional.pk),
    )
    cache.set(key, [(a.isoformat(), b.isoformat()) for a, b in free], CACHE_SECONDS)
    return free


# --- Motor --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Window:
    """Desde cuándo y hasta qué día se puede reservar. La reserva pública aplica las reglas del
    negocio (`min_notice_min`, `max_advance_days`); el panel solo impide reservar en el pasado."""

    earliest: dt.datetime
    last_day: dt.date | None


def booking_window(tenant, *, public: bool, now: dt.datetime | None = None) -> Window:
    now = now or timezone.now()
    if not public:
        return Window(earliest=now, last_day=None)
    today = timezone.localdate(now, ZoneInfo(tenant.timezone))
    return Window(
        earliest=now + dt.timedelta(minutes=tenant.min_notice_min),
        last_day=today + dt.timedelta(days=tenant.max_advance_days),
    )


def _starts(free: list[Interval], duration: dt.timedelta, step_min: int, day_start) -> list:
    """Inicios alineados a la grilla del día (cada `step_min` desde la medianoche) que caben."""
    step = dt.timedelta(minutes=step_min)
    starts = []
    for start, end in free:
        offset = (start - day_start) % step
        current = start if not offset else start + (step - offset)
        while current + duration <= end:
            starts.append(current)
            current += step
    return starts


def _overlaps(busy: list[Interval], start, end) -> bool:
    return any(busy_start < end and busy_end > start for busy_start, busy_end in busy)


def _free_resource(location_id, start, end, busy_by_resource: dict):
    for resource in catalog.active_resources(location_id):
        if not _overlaps(busy_by_resource[resource.pk], start, end):
            return resource
    return None


def resolve_services(service_ids):
    services = catalog.get_bookable_services(service_ids)
    if services is None:
        raise ApiError(
            "invalid_services",
            "Algún servicio no existe o no está activo.",
            400,
            {"service_ids": ["Revisa los servicios elegidos."]},
        )
    conflict = catalog.single_choice_conflict(services)
    if conflict is not None:
        raise ApiError(
            "one_per_category",
            f"Solo puedes elegir un servicio de «{conflict.name}» por cita.",
            400,
            {"service_ids": [f"Elige un solo servicio de «{conflict.name}»."]},
        )
    return services


def candidates(services, professional_id=None, *, public: bool):
    """Profesionales que ofrecen todos los servicios (todos, o solo el indicado)."""
    found = catalog.professionals_for_services(services, online_only=public)
    if professional_id is None:
        return found
    chosen = [p for p in found if str(p.pk) == str(professional_id)]
    if not chosen:
        raise ApiError(
            "professional_unavailable",
            "El profesional no ofrece esos servicios.",
            400,
            {"professional_id": ["No ofrece todos los servicios elegidos."]},
        )
    return chosen


def slots_for_day(
    tenant,
    services,
    day: dt.date,
    professionals,
    *,
    window: Window,
    use_cache: bool = True,
) -> list[Slot]:
    """Horarios disponibles de un día, uniendo los de los profesionales indicados."""
    if window.last_day is not None and day > window.last_day:
        return []
    tz = ZoneInfo(tenant.timezone)
    day_start, day_end = _day_bounds(day, tz)
    if day_end <= window.earliest:
        return []

    needs_resource = catalog.requires_resource(services)
    busy_by_resource: dict = defaultdict(list)
    if needs_resource:
        for resource in catalog.active_resources():
            busy_by_resource[resource.pk] = _busy_intervals(
                day_start, day_end, resource_id=resource.pk
            )

    free_at: dict[dt.datetime, list] = defaultdict(list)
    for professional in professionals:
        quote = catalog.quote(professional, services)
        if quote is None:
            continue
        duration = dt.timedelta(minutes=quote.total_duration_min)
        free = free_intervals(tenant, professional, day, use_cache=use_cache)
        for start in _starts(free, duration, tenant.slot_step_min, day_start):
            if start < window.earliest:
                continue
            if needs_resource and not _free_resource(
                professional.location_id, start, start + duration, busy_by_resource
            ):
                continue
            free_at[start].append((professional, duration))

    return [
        Slot(
            # En hora local: los límites que vienen de citas o bloqueos llegan en UTC.
            start=start.astimezone(tz),
            # Con varios profesionales la duración puede variar (overrides): se muestra la menor.
            end=(start + min(duration for _, duration in free_at[start])).astimezone(tz),
            professional_ids=tuple(p.pk for p, _ in free_at[start]),
        )
        for start in sorted(free_at)
    ]


def get_available_slots(tenant, service_ids, day: dt.date, professional_id=None, *, public: bool):
    """Función pública del motor (spec §8)."""
    services = resolve_services(service_ids)
    professionals = candidates(services, professional_id, public=public)
    return slots_for_day(
        tenant, services, day, professionals, window=booking_window(tenant, public=public)
    )


# Estado de cada día en el calendario de reserva (R7).
DAY_AVAILABLE = "available"  # hay al menos un horario libre
DAY_FULL = "full"  # se atiende, pero las citas (o el aviso mínimo) ya no dejan horarios
DAY_CLOSED = "closed"  # nadie atiende: sin horario de trabajo o bloqueado (festivo, vacaciones)
DAY_UNAVAILABLE = "unavailable"  # fuera de la ventana de reserva (pasado o muy lejano)
DAY_STATUSES = (DAY_AVAILABLE, DAY_FULL, DAY_CLOSED, DAY_UNAVAILABLE)


def _works_after(tenant, professional, day: dt.date, earliest: dt.datetime) -> bool:
    """¿El profesional atiende ese día después de `earliest`? Horario menos bloqueos; las citas
    no cuentan: un día lleno de citas sigue siendo un día de trabajo."""
    tz = ZoneInfo(tenant.timezone)
    day_start, day_end = _day_bounds(day, tz)
    blocks = TimeBlock.objects.filter(
        professional=professional, start_at__lt=day_end, end_at__gt=day_start
    )
    open_time = _subtract(
        _working_intervals(professional, day, tz), [(b.start_at, b.end_at) for b in blocks]
    )
    return any(end > earliest for _, end in open_time)


def day_status(tenant, services, day: dt.date, professionals, *, window: Window) -> str:
    """`available`, `full`, `closed` o `unavailable` (ver las constantes `DAY_*`)."""
    _, day_end = _day_bounds(day, ZoneInfo(tenant.timezone))
    if (window.last_day is not None and day > window.last_day) or day_end <= window.earliest:
        return DAY_UNAVAILABLE
    if slots_for_day(tenant, services, day, professionals, window=window):
        return DAY_AVAILABLE
    if any(_works_after(tenant, p, day, window.earliest) for p in professionals):
        return DAY_FULL
    return DAY_CLOSED


def get_month_calendar(
    tenant, service_ids, year: int, month: int, professional_id=None, *, public: bool
) -> list[tuple[dt.date, str]]:
    """Cada día del mes con su estado, para pintar el calendario con colores (R7)."""
    services = resolve_services(service_ids)
    professionals = candidates(services, professional_id, public=public)
    window = booking_window(tenant, public=public)
    day = dt.date(year, month, 1)
    calendar = []
    while day.month == month:
        calendar.append((day, day_status(tenant, services, day, professionals, window=window)))
        day += dt.timedelta(days=1)
    return calendar


def get_available_days(
    tenant, service_ids, year: int, month: int, professional_id=None, *, public: bool
):
    """Días del mes con al menos un horario disponible (spec §8.10)."""
    calendar = get_month_calendar(tenant, service_ids, year, month, professional_id, public=public)
    return [day for day, status in calendar if status == DAY_AVAILABLE]


def free_resource_for(tenant, professional, start: dt.datetime, end: dt.datetime):
    """Un puesto libre de la sede del profesional en `[start, end)`, o None."""
    tz = ZoneInfo(tenant.timezone)
    day_start, day_end = _day_bounds(timezone.localdate(start, tz), tz)
    busy_by_resource: dict = defaultdict(list)
    for resource in catalog.active_resources(professional.location_id):
        busy_by_resource[resource.pk] = _busy_intervals(
            min(day_start, start), max(day_end, end), resource_id=resource.pk
        )
    return _free_resource(professional.location_id, start, end, busy_by_resource)
