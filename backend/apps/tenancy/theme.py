"""Tema de colores de un tenant, con validación de contraste de accesibilidad (WCAG AA)."""

import re
from typing import Any

from config.api import ApiError

THEME_KEYS = ("primary", "secondary", "background", "surface", "text")
DEFAULT_THEME = {
    "primary": "#1f2937",
    "secondary": "#b45309",
    "background": "#ffffff",
    "surface": "#f3f4f6",
    "text": "#111827",
}
MIN_TEXT_CONTRAST = 4.5  # WCAG AA para texto normal

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _luminance(color: str) -> float:
    channels = []
    for index in (1, 3, 5):
        value = int(color[index : index + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """Relación de contraste WCAG entre dos colores `#rrggbb` (de 1 a 21)."""
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def validate_theme(theme: Any) -> dict[str, str]:
    """Devuelve el tema normalizado (minúsculas) o lanza ApiError con los campos inválidos.

    Exige los cinco colores y que el texto se lea sobre el fondo y sobre las superficies.
    """
    if not isinstance(theme, dict):
        raise ApiError("invalid_theme", "El tema debe ser un objeto.", 400)
    errors: dict[str, list[str]] = {}
    for key in THEME_KEYS:
        value = theme.get(key)
        if not isinstance(value, str) or not _HEX_RE.match(value):
            errors[key] = ["Debe ser un color hexadecimal de 6 dígitos, por ejemplo #1f2937."]
    unknown = sorted(set(theme) - set(THEME_KEYS))
    for key in unknown:
        errors[key] = ["Color desconocido."]
    if errors:
        raise ApiError("invalid_theme", "Tema inválido.", 400, errors)

    normalized = {key: theme[key].lower() for key in THEME_KEYS}
    for surface, label in (("background", "el fondo"), ("surface", "la superficie")):
        ratio = contrast_ratio(normalized["text"], normalized[surface])
        if ratio < MIN_TEXT_CONTRAST:
            errors.setdefault("text", []).append(
                f"Poco contraste con {label} ({ratio:.2f}:1). WCAG AA exige al menos 4.5:1."
            )
    if errors:
        raise ApiError("low_contrast", "El texto no se lee con estos colores.", 400, errors)
    return normalized
