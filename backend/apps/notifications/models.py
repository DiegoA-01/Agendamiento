from django.db import models

from apps.tenancy.models import TenantOwnedModel


class NotificationLog(TenantOwnedModel):
    """Cada mensaje que se intenta mandar a un cliente (spec §6 y §10).

    `dedupe_key` hace idempotentes las tareas: la misma cita, tipo y canal nunca se manda dos veces,
    aunque Celery reintente o el recordatorio corra de nuevo.
    """

    class Kind(models.TextChoices):
        CONFIRMATION = "confirmation"
        REMINDER = "reminder"
        CANCELLATION = "cancellation"
        RESCHEDULE = "reschedule"

    class Channel(models.TextChoices):
        EMAIL = "email"
        WHATSAPP = "whatsapp"

    class Status(models.TextChoices):
        QUEUED = "queued"
        SENT = "sent"
        FAILED = "failed"

    appointment = models.ForeignKey(
        "booking.Appointment", on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    to = models.CharField(max_length=254)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    # `<cita>:<tipo>[:<horas>]:<canal>`; los recordatorios llevan las horas de antelación.
    dedupe_key = models.CharField(max_length=150)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "dedupe_key"], name="uniq_notification_dedupe_key"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind}/{self.channel} → {self.to} ({self.status})"
