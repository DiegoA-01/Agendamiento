import uuid

from django.db import models


class AuditLog(models.Model):
    """Quién hizo qué y cuándo en la plataforma. Es un registro: no se edita ni se borra, por eso
    no sigue la convención de borrado lógico.

    Nunca guardar contraseñas ni secretos en before/after."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=60)
    entity = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=64)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.entity}:{self.entity_id}"
