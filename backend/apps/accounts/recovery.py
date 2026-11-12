"""Códigos de recuperación del 2FA (pormejorar §2).

Al activar el 2FA se entregan `COUNT` códigos de un solo uso. Cada uno reemplaza una vez al código
de 6 dígitos si se pierde el celular. Solo se guarda su SHA-256: los códigos son aleatorios y
largos (50 bits), así que no hace falta un hash lento como el de las contraseñas, y comprobar diez
de ellos en cada intento no frena el login.
"""

import hashlib
import hmac
import secrets

COUNT = 10
# Sin 0/o, 1/l/i: se leen y se copian a mano sin confusión. 31 símbolos: ≈ 5 bits cada uno.
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
GROUP = 5


def _normalize(code: str) -> str:
    return "".join(ch for ch in code.lower() if ch.isalnum())


def _digest(code: str) -> str:
    return hashlib.sha256(_normalize(code).encode()).hexdigest()


def generate(count: int = COUNT) -> tuple[list[str], list[str]]:
    """Devuelve (códigos para mostrar una sola vez, hashes para guardar)."""
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(ALPHABET) for _ in range(GROUP * 2))
        codes.append(f"{raw[:GROUP]}-{raw[GROUP:]}")
    return codes, [_digest(code) for code in codes]


def looks_like_recovery_code(code: str) -> bool:
    """Un código de la app son 6 dígitos; uno de recuperación tiene 10 caracteres con letras."""
    normalized = _normalize(code)
    return len(normalized) == GROUP * 2 and not normalized.isdigit()


def match(code: str, hashes: list[str]) -> str | None:
    """El hash guardado que corresponde al código, o None. Compara en tiempo constante."""
    digest = _digest(code)
    found = None
    for stored in hashes:
        if hmac.compare_digest(stored, digest):
            found = stored
    return found
