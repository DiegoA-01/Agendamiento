"""Auditoría de los eventos de seguridad de las cuentas (M10, pormejorar #16)."""

from django.dispatch import receiver

from apps.accounts.signals import security_event

from .services import record


@receiver(security_event, dispatch_uid="platform_admin.audit_security_event")
def audit_security_event(sender, *, request, action, user, email, **kwargs):
    """Una fila de `AuditLog` por evento. Nunca guarda contraseñas ni códigos.

    Para un correo que no existe se guarda el correo escrito (sirve para ver ataques), sin usuario.
    """
    tenant = getattr(user, "tenant", None) if user is not None else None
    if tenant is None and request is not None:
        tenant = getattr(request, "tenant", None)
    record(
        request,
        action,
        "user",
        user.pk if user is not None else "",
        tenant=tenant,
        actor=user,
        after={"email": email} if email else None,
    )
