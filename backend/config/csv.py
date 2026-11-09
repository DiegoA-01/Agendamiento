"""Exportación CSV de reportes y comisiones (spec §11)."""

import csv
import io
from collections.abc import Iterable

from django.http import HttpResponse


def csv_response(
    filename: str, header: list[str], rows: Iterable[Iterable[object]]
) -> HttpResponse:
    """CSV en UTF-8 con BOM para que Excel muestre bien las tildes; separador coma.

    Los valores que empiezan con `=`, `+`, `-` o `@` se escapan con una comilla simple para que
    una hoja de cálculo no los ejecute como fórmula (inyección CSV). Los números no se tocan.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_safe(value) for value in row])
    response = HttpResponse("\ufeff" + buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _safe(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value
