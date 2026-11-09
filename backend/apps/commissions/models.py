from django.db import models
from django.db.models import Q

from apps.tenancy.models import TenantOwnedModel

MONEY = {"max_digits": 12, "decimal_places": 2}


class ImmutableEntryError(Exception):
    """Una comisión ya registrada no se edita ni se borra: se corrige con una entrada de ajuste."""


class CommissionEntry(TenantOwnedModel):
    """Lo que gana el profesional y el negocio por un servicio de una cita completada (spec §11).

    Inmutable: se crea al completar la cita y nunca cambia. Una corrección es otra fila de tipo
    `adjustment` que apunta a la original (`adjusts`) con la diferencia, positiva o negativa. Así
    la suma de todas las filas de un servicio es siempre lo que realmente se pagó.
    """

    class Kind(models.TextChoices):
        ENTRY = "entry"
        ADJUSTMENT = "adjustment"

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.ENTRY)
    appointment = models.ForeignKey(
        "booking.Appointment", on_delete=models.PROTECT, related_name="commission_entries"
    )
    appointment_item = models.ForeignKey(
        "booking.AppointmentItem", on_delete=models.PROTECT, related_name="commission_entries"
    )
    professional = models.ForeignKey(
        "catalog.Professional", on_delete=models.PROTECT, related_name="commission_entries"
    )
    service = models.ForeignKey("catalog.Service", on_delete=models.PROTECT, related_name="+")
    # Fecha de la cita, copiada para filtrar y agrupar los reportes sin unir tablas.
    appointment_start_at = models.DateTimeField()
    base_amount = models.DecimalField(**MONEY)
    pct = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(**MONEY)
    business_amount = models.DecimalField(**MONEY)
    adjusts = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="adjustments"
    )
    reason = models.CharField(max_length=250, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ("appointment_start_at", "created_at")
        indexes = [
            models.Index(fields=["tenant", "appointment_start_at"]),
            models.Index(fields=["tenant", "professional", "appointment_start_at"]),
        ]
        constraints = [
            # Una sola entrada original por servicio de la cita: completar dos veces no duplica.
            models.UniqueConstraint(
                fields=["appointment_item"],
                condition=Q(kind="entry"),
                name="uniq_commission_entry_per_item",
            ),
            # La original no apunta a nada; un ajuste siempre apunta a la original.
            models.CheckConstraint(
                condition=(Q(kind="entry", adjusts__isnull=True))
                | Q(kind="adjustment", adjusts__isnull=False),
                name="commission_adjustment_points_to_entry",
            ),
            models.CheckConstraint(
                condition=Q(pct__gte=0, pct__lte=100), name="commission_pct_between_0_and_100"
            ),
            models.CheckConstraint(
                condition=Q(
                    base_amount=models.F("commission_amount") + models.F("business_amount")
                ),
                name="commission_amounts_add_up",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.commission_amount}"

    def save(self, *args, **kwargs) -> None:
        if not self._state.adding:
            raise ImmutableEntryError("Las comisiones no se editan; registra un ajuste.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableEntryError("Las comisiones no se borran; registra un ajuste.")
