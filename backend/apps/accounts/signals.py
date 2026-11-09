"""Eventos de seguridad de las cuentas (M10).

`accounts` no conoce el registro de auditoría: solo avisa. `platform_admin` escucha y guarda el
`AuditLog`. Así ninguna de las dos apps importa los modelos de la otra.

Argumentos: `request` (puede ser None, p. ej. desde un comando), `action`, `user` (None si el
correo no existe) y `email` (el que se escribió).
"""

from django.dispatch import Signal

security_event = Signal()

LOGIN_SUCCEEDED = "auth.login"
LOGIN_FAILED = "auth.login_failed"
LOGIN_BLOCKED = "auth.login_blocked"
PASSWORD_CHANGED = "auth.password_change"
PASSWORD_RESET_REQUESTED = "auth.password_reset_request"
PASSWORD_RESET = "auth.password_reset"
TWO_FACTOR_ENABLED = "auth.two_factor_enable"
TWO_FACTOR_RESET = "auth.two_factor_reset"


def emit(action: str, *, request=None, user=None, email: str = "") -> None:
    security_event.send(
        sender="accounts", request=request, action=action, user=user, email=email or ""
    )
