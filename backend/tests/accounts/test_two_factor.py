import time

import pytest
from rest_framework.test import APIClient

from apps.accounts import totp
from apps.accounts.models import User
from tests.factories import PASSWORD, SuperadminFactory, TenantFactory, UserFactory

from .helpers import ADMIN_HOST, enable_two_factor, host, login, post

pytestmark = pytest.mark.django_db


def now_code(secret: str, offset: int = 0) -> str:
    return totp.code_at(secret, time.time() + offset)


def setup_two_factor(client: APIClient, user: User, at: str) -> str:
    response = post(
        client, "/api/v1/auth/2fa/setup/", {"email": user.email, "password": PASSWORD}, at
    )
    assert response.status_code == 200, response.content
    return response.json()["secret"]


def test_superadmin_without_two_factor_cannot_log_in_and_gets_no_session():
    root = SuperadminFactory()
    client = APIClient()
    response = login(client, root, ADMIN_HOST)
    assert response.status_code == 403
    assert response.json()["code"] == "two_factor_setup_required"
    assert client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).status_code == 401


def test_full_enrollment_flow_then_login_needs_the_code():
    root = SuperadminFactory()
    client = APIClient()

    setup = post(
        client, "/api/v1/auth/2fa/setup/", {"email": root.email, "password": PASSWORD}, ADMIN_HOST
    )
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/Agenda:")

    wrong = post(
        client,
        "/api/v1/auth/2fa/confirm/",
        {"email": root.email, "password": PASSWORD, "code": "000000"},
        ADMIN_HOST,
    )
    assert wrong.status_code == 401
    assert wrong.json()["code"] == "invalid_two_factor_code"

    confirm = post(
        client,
        "/api/v1/auth/2fa/confirm/",
        {"email": root.email, "password": PASSWORD, "code": now_code(secret)},
        ADMIN_HOST,
    )
    assert confirm.status_code == 200
    assert confirm.json()["two_factor_enabled"] is True
    assert client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).status_code == 200

    # Nueva sesión: sin código, pide el código; con código del paso siguiente, entra.
    fresh = APIClient()
    missing = login(fresh, root, ADMIN_HOST)
    assert missing.status_code == 401
    assert missing.json()["code"] == "two_factor_required"
    assert login(fresh, root, ADMIN_HOST, totp_code="000000").json()["code"] == (
        "invalid_two_factor_code"
    )
    assert login(fresh, root, ADMIN_HOST, totp_code=now_code(secret, 30)).status_code == 200


def test_a_code_cannot_be_used_twice():
    root = SuperadminFactory()
    secret = enable_two_factor(root)
    code = now_code(secret)
    assert login(APIClient(), root, ADMIN_HOST, totp_code=code).status_code == 200
    replay = login(APIClient(), root, ADMIN_HOST, totp_code=code)
    assert replay.status_code == 401
    assert replay.json()["code"] == "invalid_two_factor_code"


def test_correct_code_with_wrong_password_is_still_rejected():
    root = SuperadminFactory()
    secret = enable_two_factor(root)
    response = login(
        APIClient(), root, ADMIN_HOST, password="otra-clave-123", totp_code=now_code(secret)
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_setup_needs_valid_credentials():
    root = SuperadminFactory()
    response = post(
        APIClient(),
        "/api/v1/auth/2fa/setup/",
        {"email": root.email, "password": "mala-clave-123"},
        ADMIN_HOST,
    )
    assert response.status_code == 401


def test_setup_is_refused_once_two_factor_is_active():
    root = SuperadminFactory()
    enable_two_factor(root)
    response = post(
        APIClient(),
        "/api/v1/auth/2fa/setup/",
        {"email": root.email, "password": PASSWORD},
        ADMIN_HOST,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "two_factor_already_enabled"


def test_confirm_without_starting_setup_is_refused():
    root = SuperadminFactory()
    response = post(
        APIClient(),
        "/api/v1/auth/2fa/confirm/",
        {"email": root.email, "password": PASSWORD, "code": "123456"},
        ADMIN_HOST,
    )
    assert response.status_code == 409


def test_owner_does_not_need_two_factor_until_enabled():
    tenant = TenantFactory(slug="elfilo")
    owner = UserFactory(tenant=tenant, role=User.Role.OWNER)
    assert login(APIClient(), owner, host("elfilo")).status_code == 200

    client = APIClient()
    secret = setup_two_factor(client, owner, host("elfilo"))
    confirm = post(
        client,
        "/api/v1/auth/2fa/confirm/",
        {"email": owner.email, "password": PASSWORD, "code": now_code(secret)},
        host("elfilo"),
    )
    assert confirm.status_code == 200

    # Ya activado, se le exige.
    assert login(APIClient(), owner, host("elfilo")).json()["code"] == "two_factor_required"
