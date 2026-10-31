"""API pública de la app booking para otras apps. M5 agrega la creación de citas y sus estados."""

import datetime as dt

from django.db.models import QuerySet

from .models import ACTIVE_STATUSES, Appointment


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
