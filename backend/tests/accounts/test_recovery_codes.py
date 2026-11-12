"""Códigos de recuperación del 2FA (pormejorar §2)."""

import re
import time

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts import recovery, totp
from apps.accounts.models import User
from apps.platform_admin.models import AuditLog
from tests.accounts.factories import PASSWORD, SuperadminFactory

from .helpers import ADMIN_HOST, enable_two_factor, login, post

pytestmark = pytest.mark.django_db

CODE_RE = re.compile(r"^[a-z2-9]{5}-[a-z2-9]{5}$")
REGENERATE = "/api/v1/auth/2fa/recovery-codes/"


def now_code(secret: str, offset: int = 0) -> str:
    return totp.code_at(secret, time.time() + offset)


def enroll(client: APIClient, root: User) -> tuple[str, list[str]]:
    """Activa el 2FA por la API. Devuelve el secreto y los códigos de recuperación."""
    setup = post(
        client, "/api/v1/auth/2fa/setup/", {"email": root.email, "password": PASSWORD}, ADMIN_HOST
    )
    secret = setup.json()["secret"]
    confirm = post(
        client,
        "/api/v1/auth/2fa/confirm/",
        {"email": root.email, "password": PASSWORD, "code": now_code(secret)},
        ADMIN_HOST,
    )
    assert confirm.status_code == 200, confirm.content
    return secret, confirm.json()["recovery_codes"]


def test_activating_two_factor_hands_out_ten_codes_stored_only_as_hashes():
    root = SuperadminFactory()
    client = APIClient()
    _, codes = enroll(client, root)

    assert len(codes) == recovery.COUNT == 10
    assert len(set(codes)) == 10
    assert all(CODE_RE.match(code) for code in codes)
    root.refresh_from_db()
    assert len(root.totp_recovery_codes) == 10
    assert not set(codes) & set(root.totp_recovery_codes)  # nunca en claro
    assert client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).json()["recovery_codes_left"] == 10


def test_a_recovery_code_logs_in_once_and_is_then_spent():
    root = SuperadminFactory()
    _, codes = enroll(APIClient(), root)

    # Se acepta con mayúsculas, sin guion o con espacios: se escribe a mano.
    first = login(APIClient(), root, ADMIN_HOST, totp_code=f" {codes[0].upper()} ")
    assert first.status_code == 200, first.content
    assert first.json()["recovery_codes_left"] == 9

    again = login(APIClient(), root, ADMIN_HOST, totp_code=codes[0])
    assert again.status_code == 401
    assert again.json()["code"] == "invalid_recovery_code"

    second = login(APIClient(), root, ADMIN_HOST, totp_code=codes[1].replace("-", ""))
    assert second.status_code == 200
    root.refresh_from_db()
    assert len(root.totp_recovery_codes) == 8

    used = AuditLog.objects.filter(action="auth.recovery_code_used")
    assert used.count() == 2
    assert all(row.after == {"email": root.email} for row in used)  # nunca el código


def test_a_made_up_recovery_code_counts_as_a_failed_attempt():
    root = SuperadminFactory()
    enroll(APIClient(), root)

    response = login(APIClient(), root, ADMIN_HOST, totp_code="abcde-fghjk")

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_recovery_code"
    assert AuditLog.objects.filter(action="auth.login_failed").exists()


def test_recovery_codes_need_the_right_password():
    root = SuperadminFactory()
    _, codes = enroll(APIClient(), root)

    response = login(APIClient(), root, ADMIN_HOST, password="otra-clave-mala", totp_code=codes[0])

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    root.refresh_from_db()
    assert len(root.totp_recovery_codes) == 10  # no se gastó


def test_regenerating_replaces_all_codes_and_asks_for_password_and_app_code():
    root = SuperadminFactory()
    client = APIClient()
    secret, old_codes = enroll(client, root)

    no_code = post(client, REGENERATE, {"password": PASSWORD, "code": "000000"}, ADMIN_HOST)
    assert no_code.status_code == 401
    assert no_code.json()["code"] == "invalid_two_factor_code"
    bad_password = post(
        client, REGENERATE, {"password": "mala", "code": now_code(secret, 30)}, ADMIN_HOST
    )
    assert bad_password.json()["code"] == "invalid_credentials"

    response = post(
        client, REGENERATE, {"password": PASSWORD, "code": now_code(secret, 30)}, ADMIN_HOST
    )
    assert response.status_code == 200, response.content
    new_codes = response.json()["recovery_codes"]
    assert len(new_codes) == 10
    assert not set(new_codes) & set(old_codes)

    # Los viejos ya no sirven; los nuevos sí.
    assert login(APIClient(), root, ADMIN_HOST, totp_code=old_codes[0]).status_code == 401
    assert login(APIClient(), root, ADMIN_HOST, totp_code=new_codes[0]).status_code == 200
    assert AuditLog.objects.filter(action="auth.recovery_codes_regenerated").count() == 1


def test_regenerating_needs_a_session_and_two_factor_on():
    root = SuperadminFactory()
    assert post(
        APIClient(), REGENERATE, {"password": PASSWORD, "code": "1"}, ADMIN_HOST
    ).status_code in (
        401,
        403,
    )

    # Un usuario con 2FA activado antes de esta mejora no tiene códigos: los puede generar.
    secret = enable_two_factor(root)
    client = APIClient()
    assert login(client, root, ADMIN_HOST, totp_code=now_code(secret)).status_code == 200
    assert client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).json()["recovery_codes_left"] == 0
    response = post(
        client, REGENERATE, {"password": PASSWORD, "code": now_code(secret, 30)}, ADMIN_HOST
    )
    assert response.status_code == 200
    assert client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).json()["recovery_codes_left"] == 10


def test_reset_2fa_command_also_drops_the_codes():
    root = SuperadminFactory()
    enroll(APIClient(), root)

    call_command("reset_2fa", email=root.email)

    root.refresh_from_db()
    assert root.totp_enabled is False
    assert root.totp_recovery_codes == []


def test_six_digits_are_still_read_as_an_app_code():
    assert not recovery.looks_like_recovery_code("123456")
    assert not recovery.looks_like_recovery_code("123 456")
    assert recovery.looks_like_recovery_code("abcde-23456")
    assert recovery.looks_like_recovery_code("ABCDE23456")
