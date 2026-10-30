from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import JsonResponse

from . import services


def requires_module(module_key: str) -> Callable:
    """Bloquea la vista (403) si el tenant de la petición no tiene el módulo habilitado.

    Sirve para funciones `view(request, ...)` y métodos `view(self, request, ...)`.
    """

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = args[0] if hasattr(args[0], "META") else args[1]
            if not services.is_module_enabled(getattr(request, "tenant", None), module_key):
                return JsonResponse(
                    {
                        "code": "module_disabled",
                        "detail": f"El módulo '{module_key}' no está habilitado.",
                        "fields": {},
                    },
                    status=403,
                )
            return view(*args, **kwargs)

        return wrapper

    return decorator
