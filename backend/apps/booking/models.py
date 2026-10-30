import secrets

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import F, Func, Q

from apps.tenancy.models import TenantOwnedModel

MONEY = {"max_digits": 12, "decimal_places": 2}


def _new_cancel_token() -> str:
    return secrets.token_urlsafe(32)


class TsTzRange(Func):
    """`tstzrange(start, end)` con límites `[)`: una cita que termina a las 10:00 no choca con
    la que empieza a las 10:00."""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Customer(TenantOwnedModel):
    """Cliente final. Reserva como invitado (sin cuenta) y se identifica por su celular."""

    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)  # E.164, p. ej. +573001234567
    birthday = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    marketing_consent = models.BooleanField(default=False)
    data_consent_at = models.DateTimeField()  # Ley 1581: autorización de tratamiento de datos

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "phone"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_customer_phone_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name


# Estados que ocupan el hueco en la agenda; los demás lo liberan (spec §7).
ACTIVE_STATUSES = ("pending", "confirmed", "in_progress")


class Appointment(TenantOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        CONFIRMED = "confirmed"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
        NO_SHOW = "no_show"
        RESCHEDULED = "rescheduled"

    class Source(models.TextChoices):
        WEB = "web"
        DASHBOARD = "dashboard"

    ACTIVE_STATUSES = ACTIVE_STATUSES

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="appointments")
    professional = models.ForeignKey(
        "catalog.Professional", on_delete=models.PROTECT, related_name="appointments"
    )
    resource = models.ForeignKey(
        "catalog.Resource",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="appointments",
    )
    location = models.ForeignKey(
        "company.Location", on_delete=models.PROTECT, related_name="appointments"
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    source = models.CharField(max_length=20, choices=Source.choices)
    price_total = models.DecimalField(**MONEY, default=0)
    cancel_token = models.CharField(max_length=64, unique=True, default=_new_cancel_token)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=250, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    rescheduled_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="rescheduled_to"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(start_at__lt=F("end_at")), name="appointment_start_before_end"
            ),
            models.CheckConstraint(
                condition=Q(price_total__gte=0), name="appointment_price_total_gte_0"
            ),
            # Anti doble reserva: un profesional no puede tener dos citas activas que se traslapen.
            ExclusionConstraint(
                name="appointment_no_overlap_professional",
                expressions=[
                    (TsTzRange("start_at", "end_at"), RangeOperators.OVERLAPS),
                    ("professional", RangeOperators.EQUAL),
                ],
                condition=Q(status__in=ACTIVE_STATUSES, deleted_at__isnull=True),
            ),
            # Lo mismo para el puesto, cuando la cita usa uno.
            ExclusionConstraint(
                name="appointment_no_overlap_resource",
                expressions=[
                    (TsTzRange("start_at", "end_at"), RangeOperators.OVERLAPS),
                    ("resource", RangeOperators.EQUAL),
                ],
                condition=Q(
                    status__in=ACTIVE_STATUSES, resource__isnull=False, deleted_at__isnull=True
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.start_at:%Y-%m-%d %H:%M} {self.status}"


class AppointmentItem(TenantOwnedModel):
    """Servicio dentro de una cita, con precio, duración y comisión congelados al reservar."""

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey("catalog.Service", on_delete=models.PROTECT, related_name="+")
    # El MVP usa el mismo profesional de la cita; el campo permite varios en el futuro.
    professional = models.ForeignKey(
        "catalog.Professional", on_delete=models.PROTECT, related_name="+"
    )
    price_charged = models.DecimalField(**MONEY)
    duration_min = models.PositiveIntegerField()
    commission_pct_snapshot = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(price_charged__gte=0), name="appointment_item_price_gte_0"
            ),
            models.CheckConstraint(
                condition=Q(duration_min__gt=0), name="appointment_item_duration_gt_0"
            ),
        ]
