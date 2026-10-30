"""TOTP (RFC 6238) con la librería estándar: el código de 6 dígitos de Google Authenticator & co."""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _hotp(secret: str, counter: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    number = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 10**DIGITS:0{DIGITS}d}"


def code_at(secret: str, at: float) -> str:
    return _hotp(secret, int(at // STEP_SECONDS))


def verify(
    secret: str,
    code: str,
    *,
    now: float | None = None,
    last_step: int | None = None,
    window: int = 1,
) -> int | None:
    """Devuelve el paso de tiempo que coincide, o None.

    Acepta ±`window` pasos (reloj desfasado) y rechaza pasos ya usados (`last_step`) para que un
    código no sirva dos veces.
    """
    code = code.strip().replace(" ", "")
    # isascii: `isdigit` acepta dígitos Unicode (p. ej. "２") y compare_digest no los admite.
    if len(code) != DIGITS or not (code.isascii() and code.isdigit()):
        return None
    current = int((time.time() if now is None else now) // STEP_SECONDS)
    for step in range(current - window, current + window + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(_hotp(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    """URI `otpauth://` para mostrar como QR (el frontend dibuja el QR)."""
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(account)}"
        f"?secret={secret}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP_SECONDS}"
    )
