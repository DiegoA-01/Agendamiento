from django.db import models
from django.db.models import F, Q

from apps.tenancy.models import TenantOwnedModel


class WorkingHours(TenantOwnedModel):
    """Franja semanal de trabajo en hora local del tenant. Varias filas por día = descanso."""

    professional = models.ForeignKey(
        "catalog.Professional", on_delete=models.CASCADE, related_name="working_hours"
    )
    weekday = models.PositiveSmallIntegerField()  # 0 = lunes ... 6 = domingo
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name_plural = "working hours"
        ordering = ["weekday", "start_time"]
        constraints = [
            models.CheckConstraint(condition=Q(weekday__lte=6), name="working_hours_weekday_0_6"),
            models.CheckConstraint(
                condition=Q(start_time__lt=F("end_time")), name="working_hours_start_before_end"
            ),
        ]


class TimeBlock(TenantOwnedModel):
    """Bloqueo de agenda de un profesional o de un puesto (exactamente uno de los dos)."""

    professional = models.ForeignKey(
        "catalog.Professional",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="time_blocks",
    )
    resource = models.ForeignKey(
        "catalog.Resource",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="time_blocks",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(professional__isnull=False, resource__isnull=True)
                | Q(professional__isnull=True, resource__isnull=False),
                name="time_block_professional_xor_resource",
            ),
            models.CheckConstraint(
                condition=Q(start_at__lt=F("end_at")), name="time_block_start_before_end"
            ),
        ]
