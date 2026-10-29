from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse


def _check_db() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        cache.set("healthz", "ok", timeout=5)
        return cache.get("healthz") == "ok"
    except Exception:
        return False


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness + dependencias. 200 si todo responde, 503 si algo falla."""
    checks = {"database": _check_db(), "redis": _check_redis()}
    ok = all(checks.values())
    body = {
        "status": "ok" if ok else "degraded",
        "checks": {name: "ok" if passed else "fail" for name, passed in checks.items()},
    }
    return JsonResponse(body, status=200 if ok else 503)
