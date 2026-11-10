"""API pública de la app notifications (M8, spec §10).

Flujo: `booking` avisa un cambio de cita (`signals.appointment_changed`) → `schedule()` decide el
canal, arma el mensaje, crea el `NotificationLog` y encola `tasks.deliver` cuando la transacción se
confirma. Los recordatorios los crea `tasks.send_reminders` desde Celery Beat.
"""

import datetime as dt
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.booking import services as booking
from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_WHATSAPP
from apps.tenancy.context import get_current_tenant

from . import providers, templates
from .models import NotificationLog

Kind = NotificationLog.Kind
Channel = NotificationLog.Channel

MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
}  # fmt: skip
WEEKDAYS = {
    "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}


def format_date(value: dt.datetime, language: str) -> str:
    if language == "en":
        return f"{WEEKDAYS['en'][value.weekday()]}, {MONTHS['en'][value.month - 1]} {value.day}"
    return f"{WEEKDAYS['es'][value.weekday()]} {value.day} de {MONTHS['es'][value.month - 1]}"


def format_time(value: dt.datetime, language: str) -> str:
    if language == "en":
        return value.strftime("%I:%M %p").lstrip("0")
    return value.strftime("%H:%M")


def manage_url(tenant, appointment) -> str:
    base = settings.PUBLIC_SITE_URL.format(host=tenancy.subdomain_host(tenant.slug))
    return f"{base}/cita/{appointment.cancel_token}"


def manage_url_for(appointment_id) -> str:
    """Enlace de la cita para el botón de WhatsApp (dentro del negocio activo)."""
    tenant = get_current_tenant()
    appointment = booking.appointment_for_notification(appointment_id)
    return manage_url(tenant, appointment) if tenant and appointment else ""


def whatsapp_allowed(tenant, appointment) -> bool:
    """WhatsApp solo con el módulo del plan y con consentimiento (spec §10): el cliente aceptó
    mensajes, o reservó él mismo en la web (allí autoriza el tratamiento de sus datos para
    gestionar la cita)."""
    customer = appointment.customer
    return (
        tenancy.is_module_enabled(tenant, MODULE_WHATSAPP)
        and bool(customer.phone)
        and (customer.marketing_consent or appointment.source == "web")
    )


def recipient(tenant, appointment) -> tuple[str, str] | None:
    """Canal principal y destinatario. WhatsApp si se permite; si no, correo; si no hay ninguno,
    nada (un cliente sin correo agendado desde el panel no recibe mensajes)."""
    if whatsapp_allowed(tenant, appointment):
        return Channel.WHATSAPP, appointment.customer.phone
    if appointment.customer.email:
        return Channel.EMAIL, appointment.customer.email
    return None


def dedupe_key(appointment_id, kind: str, channel: str, reminder_hours: int | None) -> str:
    hours = f":{reminder_hours}h" if reminder_hours is not None else ""
    return f"{appointment_id}:{kind}{hours}:{channel}"


def render_for(tenant, appointment, kind: str) -> templates.Message:
    local = appointment.start_at.astimezone(ZoneInfo(tenant.timezone))
    language = tenant.language
    variables = {
        "customer_name": appointment.customer.full_name,
        "service": ", ".join(item.service.name for item in appointment.items.all()),
        "professional": appointment.professional.display_name,
        "date": format_date(local, language),
        "time": format_time(local, language),
        "business": tenant.name,
        "manage_url": manage_url(tenant, appointment),
    }
    return templates.render(kind, language=language, vertical=tenant.vertical, variables=variables)


def create_log(
    tenant, appointment, kind: str, channel: str, to: str, *, reminder_hours: int | None = None
) -> NotificationLog | None:
    """Crea el registro en cola, o None si ese mensaje ya existe (idempotencia)."""
    message = render_for(tenant, appointment, kind)
    try:
        with transaction.atomic():
            return NotificationLog.objects.create(
                appointment=appointment,
                kind=kind,
                channel=channel,
                to=to,
                subject=message.subject,
                body=message.body,
                dedupe_key=dedupe_key(appointment.pk, kind, channel, reminder_hours),
            )
    except IntegrityError:
        return None


def schedule(
    kind: str, appointment_id, *, reminder_hours: int | None = None
) -> NotificationLog | None:
    """Programa un mensaje de la cita en el negocio activo. Se envía al confirmar la transacción."""
    from . import tasks  # tasks importa este módulo

    tenant = get_current_tenant()
    appointment = booking.appointment_for_notification(appointment_id)
    if tenant is None or appointment is None:
        return None
    target = recipient(tenant, appointment)
    if target is None:
        return None
    log = create_log(tenant, appointment, kind, *target, reminder_hours=reminder_hours)
    if log is not None:
        tasks.delay_on_commit(tasks.deliver, tenant, str(log.pk))
    return log


def fallback_to_email(log: NotificationLog) -> NotificationLog | None:
    """WhatsApp falló todos los intentos: el mismo mensaje sale por correo, si hay (spec §10)."""
    from . import tasks

    tenant = get_current_tenant()
    appointment = booking.appointment_for_notification(log.appointment_id)
    if tenant is None or appointment is None or not appointment.customer.email:
        return None
    hours = log.dedupe_key.split(":")[2] if log.kind == Kind.REMINDER else None
    try:
        with transaction.atomic():
            email_log = NotificationLog.objects.create(
                appointment=appointment,
                kind=log.kind,
                channel=Channel.EMAIL,
                to=appointment.customer.email,
                subject=log.subject,
                body=log.body,
                dedupe_key=dedupe_key(
                    appointment.pk, log.kind, Channel.EMAIL, int(hours[:-1]) if hours else None
                ),
            )
    except IntegrityError:
        return None
    tasks.delay_on_commit(tasks.deliver, tenant, str(email_log.pk))
    return email_log


def logs_for_appointment(appointment_id):
    return NotificationLog.objects.filter(appointment_id=appointment_id)


SENT, RETRY, FAILED = "sent", "retry", "failed"


def attempt_delivery(log: NotificationLog) -> str:
    """Un intento de envío. Devuelve `sent`, `retry` (quedan intentos) o `failed` (se agotaron;
    si era WhatsApp, el mismo mensaje se programa por correo). Idempotente: un mensaje que ya
    salió o ya falló no se vuelve a enviar."""
    if log.status != NotificationLog.Status.QUEUED:
        return SENT if log.status == NotificationLog.Status.SENT else FAILED

    log.attempts += 1
    try:
        if log.channel == Channel.WHATSAPP:
            providers.whatsapp_provider().send(
                to=log.to, body=log.body, manage_url=manage_url_for(log.appointment_id)
            )
        else:
            providers.send_email(to=log.to, subject=log.subject, body=log.body)
    except providers.DeliveryError as exc:
        log.error = str(exc)[:1000]
        if log.attempts < settings.NOTIFICATION_MAX_ATTEMPTS:
            log.save(update_fields=["attempts", "error", "updated_at"])
            return RETRY
        log.status = NotificationLog.Status.FAILED
        log.save(update_fields=["attempts", "error", "status", "updated_at"])
        if log.channel == Channel.WHATSAPP:
            fallback_to_email(log)
        return FAILED

    log.status = NotificationLog.Status.SENT
    log.sent_at = timezone.now()
    log.error = ""
    log.save(update_fields=["attempts", "error", "status", "sent_at", "updated_at"])
    return SENT
