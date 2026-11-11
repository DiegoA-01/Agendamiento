"""API pública de la app booking: clientes, citas y sus estados (M5).

La disponibilidad la calcula `scheduling.availability`; aquí se crea la cita. La creación vuelve a
validar el horario dentro de la transacción, pero la garantía final contra la doble reserva es la
restricción de exclusión de PostgreSQL: si dos peticiones pasan la validación a la vez, solo una
inserta y la otra recibe `409 slot_taken` con horarios sugeridos (spec §8).
"""

import datetime as dt
import re
import uuid
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.accounts import permissions as perms
from apps.catalog import services as catalog
from apps.commissions import services as commissions
from apps.tenancy.context import tenant_context
from config.api import ApiError

from . import events
from .models import ACTIVE_STATUSES, Appointment, AppointmentItem, Customer

Status = Appointment.Status

# Transiciones válidas (spec §7). Lo que no está aquí responde 409.
TRANSITIONS = {
    "confirm": ({Status.PENDING}, Status.CONFIRMED),
    "start": ({Status.CONFIRMED}, Status.IN_PROGRESS),
    "complete": ({Status.IN_PROGRESS}, Status.COMPLETED),
    "cancel": ({Status.PENDING, Status.CONFIRMED}, Status.CANCELLED),
    "no_show": ({Status.CONFIRMED}, Status.NO_SHOW),
    "reschedule": ({Status.PENDING, Status.CONFIRMED}, Status.RESCHEDULED),
}
SUGGESTIONS = 5


def _availability():
    # Import diferido: `scheduling.availability` usa `overlapping_appointments` de este módulo.
    from apps.scheduling import availability

    return availability


def invalidate_availability(tenant_id) -> None:
    """Descarta la disponibilidad en caché del negocio después de cambiar una cita."""
    _availability().invalidate(tenant_id)


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True


def not_found(entity: str) -> ApiError:
    return ApiError("not_found", f"{entity} no encontrada.", 404)


def overlapping_appointments(
    start_at: dt.datetime,
    end_at: dt.datetime,
    *,
    professional_id=None,
    resource_id=None,
) -> QuerySet[Appointment]:
    """Citas activas del profesional o del puesto que se traslapan con `[start_at, end_at)`.

    Una cita que termina justo cuando empieza el rango no se traslapa (mismo criterio que la
    restricción de exclusión). Las canceladas y los no_show no cuentan: ya liberaron el hueco.
    """
    appointments = Appointment.objects.filter(
        status__in=ACTIVE_STATUSES, start_at__lt=end_at, end_at__gt=start_at
    )
    if professional_id is not None:
        appointments = appointments.filter(professional_id=professional_id)
    if resource_id is not None:
        appointments = appointments.filter(resource_id=resource_id)
    return appointments.order_by("start_at")


# --- Clientes -----------------------------------------------------------------------------------

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone(raw: str, *, default_country_code: str = "57") -> str:
    """Celular a E.164. `300 123 4567` y `(300) 123-4567` quedan `+573001234567`."""
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+"):
        digits = f"+{default_country_code}{digits.lstrip('0')}"
    if not _E164.match(digits):
        raise ApiError(
            "validation_error",
            "Datos inválidos.",
            400,
            {"phone": ["Usa un celular válido, por ejemplo 300 123 4567."]},
        )
    return digits


def get_or_create_customer(
    *, full_name: str, phone: str, email: str = "", marketing_consent: bool = False
) -> Customer:
    """El cliente se identifica por su celular (único por negocio). Si ya existe, se actualizan
    nombre y correo con lo último que escribió; el consentimiento de datos se registra ahora."""
    phone = normalize_phone(phone)
    customer = Customer.objects.filter(phone=phone).first()
    if customer is None:
        try:
            with transaction.atomic():
                return Customer.objects.create(
                    full_name=full_name,
                    phone=phone,
                    email=email,
                    marketing_consent=marketing_consent,
                    data_consent_at=timezone.now(),
                )
        except IntegrityError:
            # Otra petición creó el mismo celular un instante antes (dos reservas a la vez).
            customer = Customer.objects.get(phone=phone)
    customer.full_name = full_name or customer.full_name
    customer.email = email or customer.email
    customer.marketing_consent = customer.marketing_consent or marketing_consent
    customer.save(update_fields=["full_name", "email", "marketing_consent", "updated_at"])
    return customer


def get_customer(customer_id) -> Customer:
    customer = Customer.objects.filter(pk=customer_id).first() if _is_uuid(customer_id) else None
    if customer is None:
        raise ApiError("validation_error", "Datos inválidos.", 400, {"customer_id": ["No existe."]})
    return customer


# --- Crear citas --------------------------------------------------------------------------------


def _suggestions(tenant, services, professionals, start: dt.datetime, *, public: bool) -> list:
    availability = _availability()
    day = timezone.localdate(start, ZoneInfo(tenant.timezone))
    slots = availability.slots_for_day(
        tenant,
        services,
        day,
        professionals,
        window=availability.booking_window(tenant, public=public),
        use_cache=False,
    )
    return [slot.start.isoformat() for slot in slots[:SUGGESTIONS]]


def _slot_taken(tenant, services, professionals, start, *, public: bool) -> ApiError:
    return ApiError(
        "slot_taken",
        "Ese horario ya no está disponible.",
        409,
        {"suggestions": _suggestions(tenant, services, professionals, start, public=public)},
    )


def _appointments_that_day(professional_ids, start: dt.datetime, tz: ZoneInfo) -> dict:
    day = timezone.localdate(start, tz)
    day_start = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
    counts = (
        Appointment.objects.filter(
            professional_id__in=professional_ids,
            status__in=ACTIVE_STATUSES,
            start_at__gte=day_start,
            start_at__lt=day_start + dt.timedelta(days=1),
        )
        .values("professional_id")
        .annotate(total=Count("id"))
    )
    return {row["professional_id"]: row["total"] for row in counts}


def _pick_professional(tenant, services, candidates, start, *, public: bool):
    """Profesionales libres en `start`, del que menos citas tiene ese día al que más (empate:
    orden alfabético, que es el orden de `candidates`). Spec §8.7."""
    availability = _availability()
    slots = availability.slots_for_day(
        tenant,
        services,
        timezone.localdate(start, ZoneInfo(tenant.timezone)),
        candidates,
        window=availability.booking_window(tenant, public=public),
        use_cache=False,
    )
    free_ids = next((set(slot.professional_ids) for slot in slots if slot.start == start), set())
    free = [p for p in candidates if p.pk in free_ids]
    load = _appointments_that_day([p.pk for p in free], start, ZoneInfo(tenant.timezone))
    return sorted(free, key=lambda p: load.get(p.pk, 0))


def create_appointment(
    tenant,
    *,
    service_ids,
    start_at: dt.datetime,
    customer: Customer,
    professional_id=None,
    source: str = Appointment.Source.DASHBOARD,
    created_by=None,
    rescheduled_from: Appointment | None = None,
) -> Appointment:
    """Crea una cita confirmada (spec §7: web y panel nacen `confirmed`).

    `professional_id=None` es "cualquiera": se asigna el profesional libre con menos citas ese día.
    La reserva web aplica las reglas del negocio (anticipación mínima, días hacia adelante y solo
    profesionales con reserva en línea).
    """
    availability = _availability()
    public = source == Appointment.Source.WEB
    services = availability.resolve_services(service_ids)
    candidates = availability.candidates(services, professional_id, public=public)
    start_at = start_at.astimezone(ZoneInfo(tenant.timezone))

    for professional in _pick_professional(tenant, services, candidates, start_at, public=public):
        quote = catalog.quote(professional, services)
        if quote is None:
            continue
        end_at = start_at + dt.timedelta(minutes=quote.total_duration_min)
        resource = None
        if quote.requires_resource:
            resource = availability.free_resource_for(tenant, professional, start_at, end_at)
            if resource is None:
                continue
        try:
            with transaction.atomic():
                _check_customer_is_free(customer, start_at, end_at)
                appointment = Appointment.objects.create(
                    customer=customer,
                    professional=professional,
                    resource=resource,
                    location_id=professional.location_id,
                    start_at=start_at,
                    end_at=end_at,
                    status=Status.CONFIRMED,
                    source=source,
                    price_total=quote.total_price,
                    created_by=created_by,
                    rescheduled_from=rescheduled_from,
                )
                AppointmentItem.objects.bulk_create(
                    [
                        AppointmentItem(
                            tenant_id=tenant.pk,
                            appointment=appointment,
                            service_id=item.service_id,
                            professional=professional,
                            price_charged=item.price,
                            duration_min=item.duration_min,
                            commission_pct_snapshot=item.commission_pct,
                        )
                        for item in quote.items
                    ]
                )
        except IntegrityError:
            # Otra petición ganó el hueco entre la validación y el insert (restricción de
            # exclusión). Con "cualquiera" se intenta con el siguiente profesional libre.
            continue
        availability.invalidate(tenant.pk)
        events.notify(events.CREATED, appointment)
        return appointment

    raise _slot_taken(tenant, services, candidates, start_at, public=public)


# --- Consultar y cambiar citas ------------------------------------------------------------------


def _own_professional_id(user):
    own = catalog.professional_for_user(user)
    return own.pk if own is not None else None


def _scope(user, action: str) -> str:
    scope = perms.scope_for(user.role, perms.APPOINTMENTS, action)
    if scope is None:
        raise ApiError("permission_denied", "No tienes permiso para esta acción.", 403)
    return scope


def own_professional_scope(user):
    """Ficha del profesional si su alcance de citas es "solo lo propio"; None si ve todas."""
    if _scope(user, "view") != perms.OWN:
        return None
    # Sin ficha enlazada no tiene citas propias: un id que no existe no deja pasar nada.
    return _own_professional_id(user) or uuid.UUID(int=0)


def require_permission(user, action: str) -> None:
    """403 si el rol no puede hacer `action` sobre citas (matriz §5)."""
    _scope(user, action)


def list_appointments(
    user,
    *,
    start_at=None,
    end_at=None,
    professional_id=None,
    status=None,
    customer_id=None,
) -> QuerySet[Appointment]:
    """Citas visibles para `user`. Un profesional solo ve las suyas (spec §5)."""
    appointments = Appointment.objects.select_related("customer").prefetch_related("items")
    if _scope(user, "view") == perms.OWN:
        appointments = appointments.filter(professional_id=_own_professional_id(user))
    if start_at is not None:
        appointments = appointments.filter(end_at__gt=start_at)
    if end_at is not None:
        appointments = appointments.filter(start_at__lt=end_at)
    if professional_id is not None:
        appointments = appointments.filter(professional_id=professional_id)
    if status:
        appointments = appointments.filter(status__in=status)
    if customer_id is not None:
        appointments = appointments.filter(customer_id=customer_id)
    return appointments.order_by("start_at", "id")


def appointments_for_report(
    *,
    start_at: dt.datetime,
    end_at: dt.datetime,
    professional_id=None,
    service_id=None,
    category_id=None,
) -> QuerySet[Appointment]:
    """Citas que empiezan en `[start_at, end_at)` para los reportes de reservas.

    Sin las `rescheduled`: esa reserva sigue viva en la cita nueva y contarla dos veces inflaría
    el total. El permiso y el alcance los decide `reports` antes de llamar.
    """
    appointments = Appointment.objects.filter(start_at__gte=start_at, start_at__lt=end_at).exclude(
        status=Appointment.Status.RESCHEDULED
    )
    if professional_id is not None:
        appointments = appointments.filter(professional_id=professional_id)
    # Por subconsulta y no por join: una cita con dos servicios no debe contar dos veces.
    if service_id is not None:
        with_service = AppointmentItem.objects.filter(service_id=service_id)
        appointments = appointments.filter(pk__in=with_service.values("appointment_id"))
    if category_id is not None:
        in_category = AppointmentItem.objects.filter(service__category_id=category_id)
        appointments = appointments.filter(pk__in=in_category.values("appointment_id"))
    return appointments


def _check_customer_is_free(customer: Customer, start_at, end_at) -> None:
    """409 si el cliente ya tiene una cita activa que se cruza con este horario (R3).

    Bloquea la fila del cliente: dos reservas simultáneas del mismo cliente se atienden en fila,
    así la segunda ve la primera. Otro cliente sí puede reservar la misma hora con otro
    profesional; con el mismo profesional lo impide la restricción de exclusión.
    """
    if customer.pk is None:
        return
    Customer.objects.select_for_update().filter(pk=customer.pk).first()
    clash = (
        Appointment.objects.filter(
            customer=customer,
            status__in=ACTIVE_STATUSES,
            start_at__lt=end_at,
            end_at__gt=start_at,
        )
        .order_by("start_at")
        .first()
    )
    if clash is not None:
        raise ApiError(
            "customer_overlap",
            "Ya tienes una cita en ese horario.",
            409,
            {
                "start_at": [timezone.localtime(clash.start_at).isoformat()],
                "appointment_id": [str(clash.pk)],
            },
        )


def get_appointment(user, appointment_id, action: str = "view") -> Appointment:
    """La cita, o 404 si no existe o es de otro profesional (404, no 403: spec §5)."""
    scope = _scope(user, action)
    appointment = (
        Appointment.objects.select_related("customer")
        .prefetch_related("items")
        .filter(pk=appointment_id)
        .first()
        if _is_uuid(appointment_id)
        else None
    )
    if appointment is None or (
        scope == perms.OWN and appointment.professional_id != _own_professional_id(user)
    ):
        raise not_found("Cita")
    return appointment


def _transition(appointment: Appointment, action: str) -> None:
    allowed, target = TRANSITIONS[action]
    if appointment.status not in allowed:
        raise ApiError(
            "invalid_transition",
            f"Una cita en estado '{appointment.status}' no puede pasar a '{target}'.",
            409,
        )
    appointment.status = target


def change_status(user, appointment_id, action: str, *, reason: str = "") -> Appointment:
    """confirm, start, complete, cancel y no_show (spec §7). Inválidas: 409."""
    appointment = get_appointment(user, appointment_id, action)
    _transition(appointment, action)
    fields = ["status", "updated_at"]
    if action == "cancel":
        appointment.cancelled_at = timezone.now()
        appointment.cancel_reason = reason
        fields += ["cancelled_at", "cancel_reason"]
    with transaction.atomic():
        appointment.save(update_fields=fields)
        if action == "complete":
            # Solo una cita completada genera comisión y cuenta en ventas (spec §7 y §11).
            commissions.record_for_appointment(appointment)
    _availability().invalidate(appointment.tenant_id)
    events.notify(events.CANCELLED if action == "cancel" else events.UPDATED, appointment)
    return appointment


def reschedule(
    user, tenant, appointment_id, *, start_at: dt.datetime, professional_id=None
) -> Appointment:
    """Mueve la cita: la original queda `rescheduled` y se crea otra enlazada con
    `rescheduled_from` (spec §7). Mismos servicios y cliente. Todo o nada: si el nuevo horario no
    está libre, la cita original no cambia."""
    original = get_appointment(user, appointment_id, "reschedule")
    _transition(original, "reschedule")
    service_ids = [str(item.service_id) for item in original.items.all()]
    with transaction.atomic():
        # Primero se libera el hueco actual: así se puede mover a un horario que se traslapa.
        original.save(update_fields=["status", "updated_at"])
        events.notify(events.UPDATED, original)
        return create_appointment(
            tenant,
            service_ids=service_ids,
            start_at=start_at,
            customer=original.customer,
            professional_id=professional_id or original.professional_id,
            source=original.source,
            created_by=user,
            rescheduled_from=original,
        )


def update_appointment(user, appointment_id, *, resource_id=...) -> Appointment:
    """Cambios que no mueven la cita. Hoy: el puesto (`resource_id`, o `None` para quitarlo).
    Para cambiar fecha, hora o profesional se usa `reschedule`."""
    appointment = get_appointment(user, appointment_id, "update")
    if resource_id is ...:
        return appointment
    if appointment.status not in ACTIVE_STATUSES:
        raise ApiError("invalid_transition", "Solo se cambia el puesto de una cita activa.", 409)
    if resource_id is None:
        appointment.resource = None
    else:
        resource = catalog.get_resource(resource_id)
        if resource is None or not resource.is_active:
            raise ApiError(
                "validation_error", "Datos inválidos.", 400, {"resource_id": ["No existe."]}
            )
        if resource.location_id != appointment.location_id:
            raise ApiError(
                "validation_error",
                "Datos inválidos.",
                400,
                {"resource_id": ["El puesto es de otra sede."]},
            )
        appointment.resource = resource
    try:
        with transaction.atomic():
            appointment.save(update_fields=["resource", "updated_at"])
    except IntegrityError as exc:
        raise ApiError("resource_taken", "El puesto está ocupado en ese horario.", 409) from exc
    _availability().invalidate(appointment.tenant_id)
    events.notify(events.UPDATED, appointment)
    return appointment


# --- Clientes del panel (M7) --------------------------------------------------------------------
#
# Los clientes no tienen fila propia en la matriz §5: los gestiona quien ve TODAS las citas
# (propietario, administrador y recepción). El profesional, con alcance "solo lo propio", no.

CUSTOMER_FIELDS = ("full_name", "email", "phone", "birthday", "notes", "marketing_consent")


def _require_customers(user, action: str) -> None:
    if _scope(user, action) != perms.ALL:
        raise ApiError("permission_denied", "No tienes permiso para esta acción.", 403)


def list_customers(user, *, search: str = "") -> QuerySet[Customer]:
    """Clientes del negocio, con su número de citas. `search` busca en nombre o celular."""
    _require_customers(user, "view")
    customers = Customer.objects.annotate(appointments_count=Count("appointments"))
    search = search.strip()
    if search:
        digits = re.sub(r"\D", "", search)
        match = Q(full_name__icontains=search)
        if len(digits) >= 3:
            match |= Q(phone__contains=digits)
        customers = customers.filter(match)
    return customers.order_by("full_name", "id")


def get_customer_for(user, customer_id, action: str = "view") -> Customer:
    _require_customers(user, action)
    customer = (
        Customer.objects.annotate(appointments_count=Count("appointments"))
        .filter(pk=customer_id)
        .first()
        if _is_uuid(customer_id)
        else None
    )
    if customer is None:
        raise ApiError("not_found", "Cliente no encontrado.", 404)
    return customer


def _phone_taken(phone: str, exclude_id=None) -> bool:
    others = Customer.objects.filter(phone=phone)
    if exclude_id is not None:
        others = others.exclude(pk=exclude_id)
    return others.exists()


def _taken_error() -> ApiError:
    return ApiError(
        "customer_exists",
        "Ya hay un cliente con ese celular.",
        409,
        {"phone": ["Ya hay un cliente con ese celular."]},
    )


def create_customer(user, **data) -> Customer:
    """Alta desde el panel. Quien lo registra confirma que el cliente autorizó el tratamiento de
    sus datos (Ley 1581): la vista exige `data_consent=true` y aquí se guarda la fecha."""
    _require_customers(user, "create")
    data["phone"] = normalize_phone(data["phone"])
    if _phone_taken(data["phone"]):
        raise _taken_error()
    try:
        with transaction.atomic():
            customer = Customer.objects.create(data_consent_at=timezone.now(), **data)
    except IntegrityError as exc:
        raise _taken_error() from exc
    return get_customer_for(user, customer.pk)


def update_customer(user, customer_id, **changes) -> Customer:
    customer = get_customer_for(user, customer_id, "update")
    if "phone" in changes:
        changes["phone"] = normalize_phone(changes["phone"])
        if _phone_taken(changes["phone"], exclude_id=customer.pk):
            raise _taken_error()
    for field, value in changes.items():
        setattr(customer, field, value)
    try:
        with transaction.atomic():
            customer.save(update_fields=[*changes, "updated_at"])
    except IntegrityError as exc:
        raise _taken_error() from exc
    return get_customer_for(user, customer.pk)


def delete_customer(user, customer_id) -> None:
    """Borrado lógico: sus citas pasadas se conservan (reportes y comisiones)."""
    customer = get_customer_for(user, customer_id, "delete")
    customer.deleted_at = timezone.now()
    customer.save(update_fields=["deleted_at", "updated_at"])


def usage_counts(tenant, *, since: dt.datetime) -> dict[str, int]:
    """Cuánto usa el negocio la agenda (S10): citas, reservas web y clientes.

    `last_30_days` cuenta las citas creadas desde `since`, no las agendadas para esas fechas: mide
    actividad. Corre dentro del negocio, así que RLS limita todo a sus filas.
    """
    with tenant_context(tenant):
        recent = Appointment.objects.filter(created_at__gte=since)
        counts = recent.aggregate(
            created=Count("id"),
            web=Count("id", filter=Q(source=Appointment.Source.WEB)),
            completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
            cancelled=Count("id", filter=Q(status=Appointment.Status.CANCELLED)),
        )
        return {
            "appointments_total": Appointment.objects.count(),
            "appointments_recent": counts["created"],
            "web_bookings_recent": counts["web"],
            "completed_recent": counts["completed"],
            "cancelled_recent": counts["cancelled"],
            "customers_total": Customer.objects.count(),
        }


# --- Para las notificaciones (M8, frente B) ------------------------------------------------------


def appointment_for_notification(appointment_id) -> Appointment | None:
    """Cita del negocio activo con lo que necesita un mensaje (cliente, profesional, servicios)."""
    if not _is_uuid(appointment_id):
        return None
    return (
        Appointment.objects.select_related("customer", "professional", "location")
        .prefetch_related("items__service")
        .filter(pk=appointment_id)
        .first()
    )


def confirmed_starting_between(start: dt.datetime, end: dt.datetime) -> list[uuid.UUID]:
    """Ids de las citas confirmadas que empiezan en `(start, end]` (recordatorios)."""
    return list(
        Appointment.objects.filter(
            status=Appointment.Status.CONFIRMED, start_at__gt=start, start_at__lte=end
        ).values_list("pk", flat=True)
    )
