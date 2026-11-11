from django.dispatch import receiver

from apps.booking import events
from apps.booking.signals import appointment_changed

from . import services
from .models import NotificationLog


@receiver(appointment_changed, dispatch_uid="notifications.on_appointment_changed")
def on_appointment_changed(sender, *, kind, appointment, **kwargs):
    """Cita nueva → confirmación (o reprogramación si viene de otra); cancelada → aviso.

    Los demás cambios (iniciar, completar, no asistió) no avisan al cliente.
    """
    if kind == events.CREATED:
        message = (
            NotificationLog.Kind.RESCHEDULE
            if appointment.rescheduled_from_id
            else NotificationLog.Kind.CONFIRMATION
        )
        services.schedule(message, appointment.pk)
    elif kind == events.CANCELLED:
        services.schedule(NotificationLog.Kind.CANCELLATION, appointment.pk)
