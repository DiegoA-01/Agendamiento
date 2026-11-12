"""Reserva pública (M6, spec §9): lo que ve y hace un cliente sin cuenta en el host del negocio.

Protecciones contra reservas basura, en este orden: honeypot (un campo oculto que solo llena un
bot), captcha si el negocio lo activa, y límites por hora (10 por IP y 5 por celular). Todo lo que
se muestra sale del negocio activo: el tenant viene del host, nunca del cliente.
"""

import datetime as dt
import json
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from config.api import ApiError
from config.net import client_ip  # noqa: F401 (la usan las vistas públicas)

from . import events
from . import services as booking
from .models import Appointment

HOUR = 60 * 60
# Solo estas se cancelan por enlace; una cita en curso o terminada ya no (spec §7).
CANCELLABLE = (Appointment.Status.PENDING, Appointment.Status.CONFIRMED)


# --- Límites y antibots -------------------------------------------------------------------------


def _over_limit(key: str, limit: int) -> bool:
    """Cuenta un intento en la ventana de una hora; True si ya pasó el límite."""
    if cache.add(key, 1, HOUR):
        return limit < 1
    try:
        return cache.incr(key) > limit
    except ValueError:  # la ventana expiró entre `add` e `incr`
        cache.set(key, 1, HOUR)
        return limit < 1


def check_rate_limits(tenant, *, ip: str, phone: str) -> None:
    """Spec §9: 10 POST por hora por IP y 5 por celular, por negocio."""
    by_ip = _over_limit(f"public-booking:ip:{tenant.pk}:{ip}", settings.PUBLIC_BOOKING_LIMIT_PER_IP)
    by_phone = _over_limit(
        f"public-booking:phone:{tenant.pk}:{phone}", settings.PUBLIC_BOOKING_LIMIT_PER_PHONE
    )
    if by_ip or by_phone:
        raise ApiError("rate_limited", "Demasiados intentos. Vuelve a intentarlo en una hora.", 429)


def verify_captcha(token: str, ip: str) -> None:
    """Valida el captcha con el proveedor configurado. Apagado por defecto."""
    if not settings.PUBLIC_BOOKING_CAPTCHA:
        return
    if not token:
        raise ApiError(
            "captcha_required", "Completa la verificación.", 400, {"captcha_token": ["Requerido."]}
        )
    data = urllib.parse.urlencode(
        {"secret": settings.CAPTCHA_SECRET, "response": token, "remoteip": ip}
    ).encode()
    try:
        with urllib.request.urlopen(settings.CAPTCHA_VERIFY_URL, data=data, timeout=5) as reply:
            ok = bool(json.loads(reply.read()).get("success"))
    except (OSError, ValueError):
        ok = False
    if not ok:
        raise ApiError("captcha_failed", "No pudimos verificar que no eres un robot.", 400)


# --- Reservar -----------------------------------------------------------------------------------


def book(tenant, request, data: dict) -> Appointment:
    """Crea la cita desde la web. `data` ya viene validado por el serializador público."""
    if data.get("website"):
        # Honeypot: el campo está oculto con CSS; una persona nunca lo llena.
        raise ApiError("validation_error", "Datos inválidos.", 400)
    ip = client_ip(request)
    verify_captcha(data.get("captcha_token", ""), ip)
    customer_data = data["customer"]
    phone = booking.normalize_phone(customer_data["phone"])
    check_rate_limits(tenant, ip=ip, phone=phone)
    customer = booking.get_or_create_customer(
        full_name=customer_data["full_name"],
        phone=phone,
        email=customer_data.get("email", ""),
        marketing_consent=data.get("marketing_consent", False),
    )
    return booking.create_appointment(
        tenant,
        service_ids=data["service_ids"],
        start_at=data["start_at"],
        customer=customer,
        professional_id=data.get("professional_id"),
        source=Appointment.Source.WEB,
        attendee_name=data.get("attendee_name", ""),
    )


# --- Gestionar por enlace -----------------------------------------------------------------------


def by_token(token: str) -> Appointment:
    appointment = (
        Appointment.objects.select_related("customer", "professional", "location")
        .prefetch_related("items__service")
        .filter(cancel_token=token)
        .first()
        if token
        else None
    )
    if appointment is None:
        raise ApiError("not_found", "Cita no encontrada.", 404)
    return appointment


def cancel_deadline(tenant, appointment: Appointment) -> dt.datetime:
    return appointment.start_at - dt.timedelta(hours=tenant.cancel_min_hours)


def can_cancel(tenant, appointment: Appointment, now: dt.datetime | None = None) -> bool:
    now = now or timezone.now()
    # Estricto: faltando justo `cancel_min_hours` (1 h) ya no se puede cancelar.
    return appointment.status in CANCELLABLE and now < cancel_deadline(tenant, appointment)


def cancel(tenant, token: str, *, reason: str = "") -> Appointment:
    """Cancelación por el cliente: solo citas pendientes o confirmadas y hasta
    `cancel_min_hours` antes de la hora (spec §9)."""
    appointment = by_token(token)
    if appointment.status not in CANCELLABLE:
        raise ApiError("invalid_transition", "Esta cita ya no se puede cancelar.", 409)
    if not can_cancel(tenant, appointment):
        local = timezone.localtime(cancel_deadline(tenant, appointment), ZoneInfo(tenant.timezone))
        raise ApiError(
            "cancel_window_closed",
            f"Solo se puede cancelar con más de {tenant.cancel_min_hours} h de anticipación "
            f"(antes de las {local:%H:%M} del {local:%d/%m}). Comunícate con el negocio.",
            409,
        )
    appointment.status = Appointment.Status.CANCELLED
    appointment.cancelled_at = timezone.now()
    appointment.cancel_reason = reason or "Cancelada por el cliente"
    appointment.save(update_fields=["status", "cancelled_at", "cancel_reason", "updated_at"])
    booking.invalidate_availability(appointment.tenant_id)
    events.notify(events.CANCELLED, appointment)
    return appointment
