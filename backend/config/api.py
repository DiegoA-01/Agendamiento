"""Formato único de errores de la API: {"code": ..., "detail": ..., "fields": {...}}."""

from typing import Any

from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

_CODE_BY_STATUS = {
    400: "bad_request",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
}


class ApiError(APIException):
    """Error de negocio con código estable: el frontend traduce por `code`, no por `detail`."""

    def __init__(
        self,
        code: str,
        detail: str,
        status_code: int = 400,
        fields: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail=detail, code=code)
        self.code = code
        self.status_code = status_code
        self.fields = fields or {}


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ApiError):
        code, detail, fields = exc.code, str(exc.detail), exc.fields
    elif isinstance(exc, ValidationError):
        code, detail = "validation_error", "Datos inválidos."
        fields = (
            response.data
            if isinstance(response.data, dict)
            else {"non_field_errors": response.data}
        )
    else:
        code = _CODE_BY_STATUS.get(response.status_code, "error")
        detail = str(response.data.get("detail", "")) if isinstance(response.data, dict) else ""
        fields = {}

    response.data = {"code": code, "detail": detail, "fields": fields}
    return response
