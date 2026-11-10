"""Tareas de Celery de las notificaciones (M8). Todas usan `TenantTask`: corren dentro del negocio
y reciben su id como primer argumento."""

import datetime as dt
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.booking import services as booking
from apps.tenancy.tasks import TenantTask, delay_on_commit

from . import services
from .models import NotificationLog

logger = logging.getLogger(__name__)

__all__ = ["deliver", "send_reminders", "delay_on_commit"]

# Ventana de búsqueda de los recordatorios: Beat corre cada 5 minutos; con 30 minutos una caída
# corta del worker no hace perder recordatorios, y la clave de idempotencia evita duplicados.
REMINDER_WINDOW = dt.timedelta(minutes=30)


def backoff_seconds(attempt: int) -> int:
    """Espera antes del siguiente intento: 1, 2, 4… minutos."""
    return 60 * 2 ** (attempt - 1)


@shared_task(base=TenantTask, bind=True, name="notifications.deliver", max_retries=None)
def deliver(self, tenant_id, log_id):
    """Envía un mensaje registrado, con hasta `NOTIFICATION_MAX_ATTEMPTS` intentos y espera
    creciente entre ellos (`services.attempt_delivery` decide; aquí solo se reprograma)."""
    log = NotificationLog.objects.filter(pk=log_id).first()
    if log is None:
        return None
    outcome = services.attempt_delivery(log)
    if outcome == services.RETRY:
        raise self.retry(countdown=backoff_seconds(log.attempts))
    if outcome == services.FAILED:
        logger.warning(
            "Notificación fallida",
            extra={"log_id": str(log.pk), "channel": log.channel, "kind": log.kind},
        )
    return outcome


@shared_task(base=TenantTask, name="notifications.send_reminders")
def send_reminders(tenant_id) -> int:
    """Programa los recordatorios de las citas que empiezan dentro de 24 h y de 2 h (configurable
    en `NOTIFICATION_REMINDER_HOURS`). Corre por negocio desde Celery Beat."""
    now = timezone.now()
    scheduled = 0
    for hours in settings.NOTIFICATION_REMINDER_HOURS:
        target = now + dt.timedelta(hours=hours)
        for appointment_id in booking.confirmed_starting_between(target - REMINDER_WINDOW, target):
            if services.schedule(
                NotificationLog.Kind.REMINDER, appointment_id, reminder_hours=hours
            ):
                scheduled += 1
    return scheduled
