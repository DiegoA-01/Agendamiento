"""Cómo documentar en OpenAPI la autenticación por sesión (cookie `sessionid` + token CSRF)."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SessionAuthScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.SessionAuth"
    name = "sessionAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "sessionid",
            "description": "Cookie de sesión. Las peticiones que cambian datos también exigen el "
            "header X-CSRFToken (cookie csrftoken, se obtiene en GET /api/v1/auth/csrf/).",
        }


class CsrfEnforcedSessionAuthScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.CsrfEnforcedSessionAuth"
    name = "sessionAuthCsrf"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "sessionid",
            "description": "Como sessionAuth, pero el header X-CSRFToken es obligatorio también "
            "sin sesión (login, 2FA y recuperación de contraseña).",
        }
