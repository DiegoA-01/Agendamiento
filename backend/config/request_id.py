"""Identificador de cada petición (M10, pormejorar #18).

Cada petición recibe un `request_id`: el que mande el proxy en `X-Request-ID` (si es un valor
razonable) o uno nuevo. Va en cada línea de log y vuelve en el header `X-Request-ID`, así un
error que reporta un cliente se encuentra con un solo valor.
"""

import re
import uuid
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

HEADER = "X-Request-ID"
_VALID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_request_id: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id.get()


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.META.get("HTTP_X_REQUEST_ID", "")
        request_id = incoming if _VALID.match(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        token = _request_id.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _request_id.reset(token)
        response[HEADER] = request_id
        return response
