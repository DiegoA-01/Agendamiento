from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

from . import services
from .context import tenant_context

# Rutas que no dependen de un tenant (healthcheck de Docker/monitoreo y documentación).
EXEMPT_PATHS = ("/healthz/", "/api/schema/")


def request_host(request: HttpRequest) -> str:
    raw = request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME", "")
    return raw.split(":")[0].strip().lower().rstrip(".")


class TenantMiddleware:
    """Resuelve el tenant por `Host` y lo activa durante la petición.

    - `admin.<BASE_DOMAIN>`: contexto Super Admin (sin tenant).
    - Host con `Domain` verificado: activa ese tenant (ContextVar + RLS).
    - Cualquier otro host: 404.

    Ojo (M7, SSE): el tenant se desactiva al volver la vista; una respuesta en streaming que
    consulte la base después de eso no tendría tenant. El endpoint SSE deberá reactivarlo.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.tenant = None
        request.is_platform_admin = False

        if request.path in EXEMPT_PATHS:
            return self.get_response(request)

        host = request_host(request)
        if host == services.admin_host():
            request.is_platform_admin = True
            return self.get_response(request)

        domain = services.resolve_domain(host)
        if domain is None:
            return JsonResponse(
                {"code": "unknown_host", "detail": "Host desconocido.", "fields": {}}, status=404
            )

        request.tenant = domain.tenant
        with tenant_context(domain.tenant):
            return self.get_response(request)
