from collections.abc import Callable

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse

from .models import User


class TenantSessionGuardMiddleware:
    """Una sesión solo vale en el host al que pertenece el usuario.

    Las cookies ya son por host, pero esto cierra la puerta aunque alguien copie una cookie:
    - Host de un tenant: el usuario debe ser de ese tenant.
    - Host `admin.`: el usuario debe ser Super Admin.
    En cualquier otro caso la petición se trata como anónima.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        if user.is_authenticated:
            if request.is_platform_admin:
                allowed = user.role == User.Role.SUPERADMIN
            elif request.tenant is not None:
                allowed = user.tenant_id == request.tenant.pk
            else:
                allowed = True  # rutas sin tenant (healthz, schema)
            if not allowed:
                request.user = AnonymousUser()
        return self.get_response(request)
