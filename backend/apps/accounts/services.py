"""Lógica de cuentas: login, 2FA, recuperación de contraseña y /me/. Las vistas solo llaman aquí."""

from functools import lru_cache
from typing import Any

from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.http import HttpRequest
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.tenancy import services as tenancy
from config.api import ApiError

from . import totp
from .backends import BACKEND_PATH
from .messages import PASSWORD_RESET
from .models import User

# Roles a los que se les exige 2FA. Propietario: opcional por ahora (si lo activa, se le exige).
REQUIRED_2FA_ROLES = frozenset({User.Role.SUPERADMIN})
TOTP_ISSUER = "Agenda"


def _scope_tenant(request: HttpRequest):
    """Tenant donde se intenta entrar, o None si es el host de plataforma (Super Admin)."""
    if request.is_platform_admin:
        return None
    if request.tenant is None:
        raise ApiError("unknown_host", "Host desconocido.", 404)
    return request.tenant


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return make_password("dummy-password-for-timing")


def _authenticate(request: HttpRequest, email: str, password: str) -> User:
    """Valida correo y contraseña dentro del tenant del host. Mismo error si algo falla, y mismo
    tiempo de respuesta exista o no el correo, para no revelar qué correos están registrados."""
    tenant = _scope_tenant(request)
    user = User.objects.for_tenant(tenant).filter(email=email.strip().lower()).first()
    if user is None:
        check_password(password, _dummy_hash())
    elif user.is_active and user.check_password(password):
        return user
    raise ApiError("invalid_credentials", "Correo o contraseña incorrectos.", 401)


def _verify_totp(user: User, code: str) -> bool:
    step = totp.verify(user.totp_secret, code, last_step=user.totp_last_step)
    if step is None:
        return False
    user.totp_last_step = step
    user.save(update_fields=["totp_last_step", "updated_at"])
    return True


def login(request: HttpRequest, email: str, password: str, totp_code: str = "") -> User:
    user = _authenticate(request, email, password)
    if user.totp_enabled:
        if not totp_code:
            raise ApiError("two_factor_required", "Falta el código de verificación.", 401)
        if not _verify_totp(user, totp_code):
            raise ApiError("invalid_two_factor_code", "Código de verificación incorrecto.", 401)
    elif user.role in REQUIRED_2FA_ROLES:
        raise ApiError(
            "two_factor_setup_required", "Debes activar la verificación en dos pasos.", 403
        )
    django_login(request, user, backend=BACKEND_PATH)
    return user


def logout(request: HttpRequest) -> None:
    django_logout(request)


def begin_two_factor_setup(request: HttpRequest, email: str, password: str) -> dict[str, str]:
    """Genera el secreto TOTP (aún sin activar). Se confirma con `confirm_two_factor`."""
    user = _authenticate(request, email, password)
    if user.totp_enabled:
        raise ApiError("two_factor_already_enabled", "La verificación ya está activa.", 409)
    user.totp_secret = totp.generate_secret()
    user.save(update_fields=["totp_secret", "updated_at"])
    return {
        "secret": user.totp_secret,
        "otpauth_uri": totp.provisioning_uri(user.totp_secret, user.email, TOTP_ISSUER),
    }


def confirm_two_factor(request: HttpRequest, email: str, password: str, code: str) -> User:
    """Activa el 2FA con un primer código válido y deja la sesión iniciada."""
    user = _authenticate(request, email, password)
    if user.totp_enabled or not user.totp_secret:
        raise ApiError("two_factor_setup_not_started", "Primero inicia la configuración.", 409)
    if not _verify_totp(user, code):
        raise ApiError("invalid_two_factor_code", "Código de verificación incorrecto.", 401)
    user.totp_enabled = True
    user.save(update_fields=["totp_enabled", "updated_at"])
    django_login(request, user, backend=BACKEND_PATH)
    return user


def request_password_reset(request: HttpRequest, email: str) -> None:
    """Envía el enlace si el correo existe en este tenant. No dice si existe o no."""
    tenant = _scope_tenant(request)
    user = (
        User.objects.for_tenant(tenant).filter(email=email.strip().lower(), is_active=True).first()
    )
    if user is None:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = request.build_absolute_uri(f"/recuperar/confirmar?uid={uid}&token={token}")
    language = tenant.language if tenant is not None else "es"
    text = PASSWORD_RESET.get(language, PASSWORD_RESET["es"])
    send_mail(
        text["subject"],
        text["body"].format(name=user.full_name, link=link),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def confirm_password_reset(request: HttpRequest, uid: str, token: str, new_password: str) -> None:
    tenant = _scope_tenant(request)
    try:
        user = (
            User.objects.for_tenant(tenant).filter(pk=force_str(urlsafe_base64_decode(uid))).first()
        )
    except (ValueError, TypeError, OverflowError, DjangoValidationError):
        user = None
    if user is None or not user.is_active or not default_token_generator.check_token(user, token):
        raise ApiError("invalid_reset_token", "El enlace no es válido o venció.", 400)
    try:
        validate_password(new_password, user)
    except DjangoValidationError as exc:
        raise ApiError(
            "weak_password",
            "La contraseña no es segura.",
            400,
            {"new_password": list(exc.messages)},
        ) from exc
    # Cambiar la contraseña invalida el token y todas las sesiones abiertas de ese usuario.
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])


def build_me(request: HttpRequest, user: User) -> dict[str, Any]:
    tenant = request.tenant
    return {
        "user": {
            "id": str(user.pk),
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
        },
        "role": user.role,
        "two_factor_enabled": user.totp_enabled,
        "is_platform_admin": user.role == User.Role.SUPERADMIN,
        "tenant": None
        if tenant is None
        else {
            "id": str(tenant.pk),
            "name": tenant.name,
            "slug": tenant.slug,
            "vertical": tenant.vertical,
            "timezone": tenant.timezone,
            "currency": tenant.currency,
            "language": tenant.language,
        },
        "theme": tenant.theme if tenant is not None else {},
        "modules": sorted(tenancy.enabled_module_keys(tenant)) if tenant is not None else [],
    }
