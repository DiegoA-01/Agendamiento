from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts import totp
from apps.accounts.models import User
from tests.factories import PASSWORD


def host(slug: str) -> str:
    return f"{slug}.{settings.BASE_DOMAIN}"


ADMIN_HOST = f"admin.{settings.BASE_DOMAIN}"


def post(client: APIClient, path: str, data: dict, at: str):
    return client.post(path, data, format="json", HTTP_HOST=at)


def login(client: APIClient, user: User, at: str, password: str = PASSWORD, **extra):
    return post(
        client, "/api/v1/auth/login/", {"email": user.email, "password": password, **extra}, at
    )


def enable_two_factor(user: User) -> str:
    """Deja el 2FA activo para el usuario sin pasar por la API. Devuelve el secreto."""
    user.totp_secret = totp.generate_secret()
    user.totp_enabled = True
    user.save()
    return user.totp_secret
