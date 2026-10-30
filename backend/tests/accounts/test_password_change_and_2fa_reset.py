import time
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from apps.accounts import totp
from apps.accounts.models import User
from tests.factories import PASSWORD, SuperadminFactory, TenantFactory, UserFactory

from .helpers import ADMIN_HOST, enable_two_factor, host, login, post

pytestmark = pytest.mark.django_db

NEW = "Una-Clave-Nueva-2026!"


@pytest.fixture
def camila():
    return UserFactory(tenant=TenantFactory(slug="elfilo"), email="camila@x.com")


def change(client, current, new, at):
    return post(
        client,
        "/api/v1/auth/password-change/",
        {"current_password": current, "new_password": new},
        at,
    )


def test_me_reports_whether_the_password_must_change(camila):
    User.objects.filter(pk=camila.pk).update(must_change_password=True)
    client = APIClient()
    assert login(client, camila, host("elfilo")).json()["must_change_password"] is True
    assert (
        client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).json()["must_change_password"] is True
    )


def test_password_change_clears_the_flag_and_keeps_this_session_only(camila):
    User.objects.filter(pk=camila.pk).update(must_change_password=True)
    here, elsewhere = APIClient(), APIClient()
    login(here, camila, host("elfilo"))
    login(elsewhere, camila, host("elfilo"))

    response = change(here, PASSWORD, NEW, host("elfilo"))
    assert response.status_code == 200
    assert response.json()["must_change_password"] is False
    assert here.get("/api/v1/me/", HTTP_HOST=host("elfilo")).status_code == 200
    assert elsewhere.get("/api/v1/me/", HTTP_HOST=host("elfilo")).status_code == 401
    assert login(APIClient(), camila, host("elfilo"), password=NEW).status_code == 200
    assert login(APIClient(), camila, host("elfilo")).status_code == 401


def test_password_change_rejects_wrong_current_password(camila):
    client = APIClient()
    login(client, camila, host("elfilo"))
    response = change(client, "no-es-la-clave", NEW, host("elfilo"))
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_current_password"
    camila.refresh_from_db()
    assert camila.check_password(PASSWORD)


def test_password_change_rejects_weak_passwords(camila):
    client = APIClient()
    login(client, camila, host("elfilo"))
    response = change(client, PASSWORD, "12345678", host("elfilo"))
    assert response.status_code == 400
    assert response.json()["code"] == "weak_password"
    assert response.json()["fields"]["new_password"]


def test_password_change_requires_a_session():
    TenantFactory(slug="elfilo")
    assert change(APIClient(), PASSWORD, NEW, host("elfilo")).status_code == 401


# --- reset_2fa ---------------------------------------------------------------------------------


def test_reset_2fa_lets_a_locked_out_superadmin_enroll_again():
    root = SuperadminFactory(email="root@demo.com")
    old_secret = enable_two_factor(root)
    assert login(APIClient(), root, ADMIN_HOST).json()["code"] == "two_factor_required"

    out = StringIO()
    call_command("reset_2fa", email="ROOT@demo.com", stdout=out)
    assert "2FA quitado" in out.getvalue()
    root.refresh_from_db()
    assert (root.totp_secret, root.totp_enabled, root.totp_last_step) == ("", False, None)

    # Sin 2FA, el login exige activarlo de nuevo; el secreto viejo ya no sirve.
    assert login(APIClient(), root, ADMIN_HOST).json()["code"] == "two_factor_setup_required"
    client = APIClient()
    new_secret = post(
        client, "/api/v1/auth/2fa/setup/", {"email": root.email, "password": PASSWORD}, ADMIN_HOST
    ).json()["secret"]
    assert new_secret != old_secret
    confirm = post(
        client,
        "/api/v1/auth/2fa/confirm/",
        {"email": root.email, "password": PASSWORD, "code": totp.code_at(new_secret, time.time())},
        ADMIN_HOST,
    )
    assert confirm.status_code == 200


def test_reset_2fa_for_a_business_user_needs_the_tenant_slug(camila):
    enable_two_factor(camila)
    with pytest.raises(CommandError, match="No existe el usuario"):
        call_command("reset_2fa", email="camila@x.com")  # busca solo entre Super Admins
    call_command("reset_2fa", email="camila@x.com", tenant="elfilo")
    camila.refresh_from_db()
    assert camila.totp_enabled is False


def test_reset_2fa_reports_unknown_tenant_and_user():
    with pytest.raises(CommandError, match="No existe el negocio"):
        call_command("reset_2fa", email="a@x.com", tenant="inventado")
    with pytest.raises(CommandError, match="No existe el usuario"):
        call_command("reset_2fa", email="nadie@x.com")
