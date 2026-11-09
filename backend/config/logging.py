import json
import logging
from datetime import UTC, datetime


def _context() -> dict[str, str]:
    """Petición y negocio activos, si los hay. Importa tarde: el logging se configura antes de
    que Django cargue las apps."""
    data: dict[str, str] = {}
    try:
        from config.request_id import get_request_id

        if request_id := get_request_id():
            data["request_id"] = request_id
        from apps.tenancy.context import get_current_tenant

        if (tenant := get_current_tenant()) is not None:
            data["tenant"] = tenant.slug
    except Exception:  # noqa: BLE001 (un log nunca debe fallar por el contexto)
        pass
    return data


class JsonFormatter(logging.Formatter):
    """Logs estructurados en JSON, una línea por registro, con `request_id` y `tenant` cuando
    existen (M10)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_context(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
