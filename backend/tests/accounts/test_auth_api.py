import time

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import totp
from apps.accounts.models import User
from tests.factories import (
    PASSWORD,
    PlanFactory,
    SuperadminFactory,
    TenantFactory,
    UserFactory,
)

from .helpers import ADMIN_HOST, enable_two_factor, host, login, post

pytestmark = pytest.mark.django_db


@pytest.fixture
def elfilo():
    return TenantFactory(slug="elfilo", plan=PlanFactory(modules=["reports", "booking"]))


@pytest.fixture
def camila(elfilo):
    return UserFactory(tenant=elfilo, email="camila@x.com", role=User.Role.RECEPTIONIST)


def test_login_sets_http_only_session_and_me_works(camila):
    client = APIClient()
    response = login(client, camila, host("elfilo"))
    assert response.status_code == 200
    assert response.json()["role"] == "receptionist"
    assert response.cookies["sessionid"]["httponly"]

    me = client.get("/api/v1/me/", HTTP_HOST=host("elfilo"))
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["email"] == "camila@x.com"
    assert body["tenant"]["slug"] == "elfilo"
    assert body["modules"] == ["booking", "reports"]
    assert body["is_platform_admin"] is False


def test_me_exposes_theme_and_tenant_settings(elfilo):
    elfilo.theme = {"primary": "#112233"}
    elfilo.save()
    owner = UserFactory(tenant=elfilo, role=User.Role.OWNER)
    client = APIClient()
    login(client, owner, host("elfilo"))
    body = client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).json()
    assert body["theme"] == {"primary": "#112233"}
    assert (body["tenant"]["timezone"], body["tenant"]["currency"]) == ("America/Bogota", "COP")


def test_wrong_password_and_unknown_email_are_indistinguishable(camila):
    wrong = login(APIClient(), camila, host("elfilo"), password="otra-clave-123")
    unknown = post(
        APIClient(),
        "/api/v1/auth/login/",
        {"email": "nadie@x.com", "password": PASSWORD},
        host("elfilo"),
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["code"] == "invalid_credentials"


def test_login_ignores_email_case_and_spaces(camila):
    response = post(
        APIClient(),
        "/api/v1/auth/login/",
        {"email": "  CAMILA@x.com ", "password": PASSWORD},
        host("elfilo"),
    )
    assert response.status_code == 200


def test_user_cannot_log_in_on_another_tenants_host(camila):
    TenantFactory(slug="aura")
    assert login(APIClient(), camila, host("aura")).status_code == 401


def test_same_email_in_two_tenants_uses_each_tenants_own_password(camila):
    aura = TenantFactory(slug="aura")
    UserFactory(tenant=aura, email="camila@x.com", password="Clave-De-Aura-2026!")
    assert login(APIClient(), camila, host("aura")).status_code == 401
    assert (
        login(APIClient(), camila, host("aura"), password="Clave-De-Aura-2026!").status_code == 200
    )
    assert login(APIClient(), camila, host("elfilo")).status_code == 200


def test_superadmin_cannot_log_in_on_a_tenant_host_nor_tenant_user_on_admin_host(camila):
    root = SuperadminFactory()
    enable_two_factor(root)
    assert login(APIClient(), root, host("elfilo")).status_code == 401
    assert login(APIClient(), camila, ADMIN_HOST).status_code == 401


@pytest.mark.parametrize("breakage", ["inactive", "deleted"])
def test_inactive_or_deleted_users_cannot_log_in(camila, breakage):
    if breakage == "inactive":
        User.objects.filter(pk=camila.pk).update(is_active=False)
    else:
        User.objects.filter(pk=camila.pk).update(deleted_at=timezone.now())
    assert login(APIClient(), camila, host("elfilo")).status_code == 401


def test_deleting_a_user_kills_their_open_session(camila):
    client = APIClient()
    login(client, camila, host("elfilo"))
    assert client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).status_code == 200
    User.objects.filter(pk=camila.pk).update(deleted_at=timezone.now())
    assert client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).status_code == 401


def test_logout_ends_the_session(camila):
    client = APIClient()
    login(client, camila, host("elfilo"))
    assert post(client, "/api/v1/auth/logout/", {}, host("elfilo")).status_code == 204
    assert client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).status_code == 401


def test_me_without_session_is_401_with_code():
    response = APIClient().get("/api/v1/me/", HTTP_HOST=host("elfilo"))
    assert response.status_code == 404  # host sin tenant
    TenantFactory(slug="elfilo")
    response = APIClient().get("/api/v1/me/", HTTP_HOST=host("elfilo"))
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_session_copied_to_another_host_is_rejected(camila):
    """Aunque alguien copie la cookie, no sirve en otro host (guardia de sesión)."""
    TenantFactory(slug="aura")
    client = APIClient()
    login(client, camila, host("elfilo"))
    assert client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).status_code == 200
    assert client.get("/api/v1/me/", HTTP_HOST=host("aura")).status_code == 401
    assert client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).status_code == 401


def test_changing_the_password_closes_existing_sessions(camila):
    client = APIClient()
    login(client, camila, host("elfilo"))
    camila.set_password("Otra-Clave-Nueva-2026!")
    camila.save()
    assert client.get("/api/v1/me/", HTTP_HOST=host("elfilo")).status_code == 401


def test_superadmin_me_has_no_tenant_and_no_modules():
    root = SuperadminFactory()
    secret = enable_two_factor(root)
    client = APIClient()
    code = totp.code_at(secret, time.time())
    assert login(client, root, ADMIN_HOST, totp_code=code).status_code == 200
    body = client.get("/api/v1/me/", HTTP_HOST=ADMIN_HOST).json()
    assert body["is_platform_admin"] is True
    assert body["tenant"] is None
    assert body["modules"] == []


def test_validation_errors_use_the_standard_format():
    TenantFactory(slug="elfilo")
    response = post(APIClient(), "/api/v1/auth/login/", {"email": "no-es-correo"}, host("elfilo"))
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert set(body["fields"]) == {"email", "password"}


def test_unknown_host_is_404_on_the_api():
    response = post(APIClient(), "/api/v1/auth/login/", {}, host("inventado"))
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_host"


def test_csrf_is_required_even_for_login(camila):
    client = APIClient(enforce_csrf_checks=True)
    data = {"email": camila.email, "password": PASSWORD}
    assert post(client, "/api/v1/auth/login/", data, host("elfilo")).status_code == 403

    csrf = client.get("/api/v1/auth/csrf/", HTTP_HOST=host("elfilo"))
    assert csrf.status_code == 204
    token = client.cookies["csrftoken"].value
    response = client.post(
        "/api/v1/auth/login/",
        data,
        format="json",
        HTTP_HOST=host("elfilo"),
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200


def test_logout_requires_csrf_when_logged_in(camila):
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/v1/auth/csrf/", HTTP_HOST=host("elfilo"))
    token = client.cookies["csrftoken"].value
    client.post(
        "/api/v1/auth/login/",
        {"email": camila.email, "password": PASSWORD},
        format="json",
        HTTP_HOST=host("elfilo"),
        HTTP_X_CSRFTOKEN=token,
    )
    assert post(client, "/api/v1/auth/logout/", {}, host("elfilo")).status_code == 403


def test_openapi_documents_the_auth_endpoints():
    response = APIClient().get("/api/schema/?format=json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in ("/api/v1/auth/login/", "/api/v1/auth/2fa/setup/", "/api/v1/me/"):
        assert path in paths


def test_logout_works_with_the_csrf_token_issued_at_login(camila):
    """Django rota el token CSRF al iniciar sesión: el frontend debe releer la cookie."""
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/v1/auth/csrf/", HTTP_HOST=host("elfilo"))
    before = client.cookies["csrftoken"].value
    client.post(
        "/api/v1/auth/login/",
        {"email": camila.email, "password": PASSWORD},
        format="json",
        HTTP_HOST=host("elfilo"),
        HTTP_X_CSRFTOKEN=before,
    )
    after = client.cookies["csrftoken"].value
    assert after != before

    stale = client.post("/api/v1/auth/logout/", HTTP_HOST=host("elfilo"), HTTP_X_CSRFTOKEN=before)
    assert stale.status_code == 403
    fresh = client.post("/api/v1/auth/logout/", HTTP_HOST=host("elfilo"), HTTP_X_CSRFTOKEN=after)
    assert fresh.status_code == 204
