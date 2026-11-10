"""Límite de intentos de inicio de sesión y de recuperación de contraseña (M10).

Se cuentan los **fallos** por IP y por correo en una ventana (`AUTH_LIMIT_WINDOW` segundos):
- Solo por IP, un atacante con muchas IP no se frena.
- Solo por correo, cualquiera podría bloquear la cuenta de otra persona a propósito; por eso el
  límite por correo es más alto que el de una persona que se equivoca y un acierto lo reinicia.
La recuperación de contraseña cuenta cada solicitud, porque siempre responde igual.
"""

import hashlib

from django.conf import settings
from django.core.cache import cache

from config.api import ApiError


def _key(kind: str, scope: str, value: str) -> str:
    # El correo va resumido: no hace falta guardarlo en Redis.
    digest = hashlib.sha256(value.strip().lower().encode()).hexdigest()[:32]
    return f"auth-limit:{kind}:{scope}:{digest}"


def _count(key: str) -> int:
    return int(cache.get(key) or 0)


def _increment(key: str) -> None:
    window = settings.AUTH_LIMIT_WINDOW
    if cache.add(key, 1, window):
        return
    try:
        cache.incr(key)
    except ValueError:  # la ventana expiró entre `add` e `incr`
        cache.set(key, 1, window)


def _blocked() -> ApiError:
    minutes = max(1, settings.AUTH_LIMIT_WINDOW // 60)
    return ApiError(
        "rate_limited",
        f"Demasiados intentos. Vuelve a intentarlo en {minutes} minutos.",
        429,
    )


def is_blocked(scope: str, ip: str, email: str) -> bool:
    return (
        _count(_key("login-ip", scope, ip)) >= settings.AUTH_LIMIT_PER_IP
        or _count(_key("login-email", scope, email)) >= settings.AUTH_LIMIT_PER_EMAIL
    )


def check_login(scope: str, ip: str, email: str) -> None:
    """429 si la IP o el correo ya pasaron el límite de fallos."""
    if is_blocked(scope, ip, email):
        raise _blocked()


def record_failure(scope: str, ip: str, email: str) -> None:
    _increment(_key("login-ip", scope, ip))
    _increment(_key("login-email", scope, email))


def clear_email(scope: str, email: str) -> None:
    """Tras un acierto, los fallos previos de ese correo dejan de contar."""
    cache.delete(_key("login-email", scope, email))


def check_password_reset(scope: str, ip: str, email: str) -> None:
    """Cuenta cada solicitud de recuperación; 429 si pasa el límite."""
    ip_key = _key("reset-ip", scope, ip)
    email_key = _key("reset-email", scope, email)
    if (
        _count(ip_key) >= settings.PASSWORD_RESET_LIMIT_PER_IP
        or _count(email_key) >= settings.PASSWORD_RESET_LIMIT_PER_EMAIL
    ):
        raise _blocked()
    _increment(ip_key)
    _increment(email_key)
