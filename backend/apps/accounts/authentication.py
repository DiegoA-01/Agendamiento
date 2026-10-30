from rest_framework.authentication import SessionAuthentication


class SessionAuth(SessionAuthentication):
    """Sesión por cookie. `authenticate_header` hace que "sin sesión" responda 401 y no 403."""

    def authenticate_header(self, request) -> str:
        return "Session"


class CsrfEnforcedSessionAuth(SessionAuth):
    """Igual, pero exige token CSRF también a usuarios anónimos (login, reset de contraseña),
    para evitar "login CSRF". El frontend obtiene el token con GET /api/v1/auth/csrf/."""

    def authenticate(self, request):
        user = getattr(request._request, "user", None)
        self.enforce_csrf(request)
        if not user or not user.is_active:
            return None
        return (user, None)
