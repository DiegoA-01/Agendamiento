"""M10: límite de intentos, auditoría de seguridad y logs con identificador de petición."""

import json
import logging
import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts import services as accounts
from apps.platform_admin.models import AuditLog
from apps.tenancy.context import tenant_context
from config.logging import JsonFormatter
from tests.accounts.factories import PASSWORD, UserFactory
from tests.accounts.helpers import host, login, post
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant():
    return TenantFactory()


@pytest.fixture
def limits(settings):
    settings.AUTH_LIMIT_PER_IP = 5
    settings.AUTH_LIMIT_PER_EMAIL = 3
    settings.PASSWORD_RESET_LIMIT_PER_IP = 4
    settings.PASSWORD_RESET_LIMIT_PER_EMAIL = 2
    return settings


def client_from(ip: str | None = None) -> APIClient:
    """Cada prueba usa su propia IP: los contadores viven en Redis entre pruebas."""
    return APIClient(REMOTE_ADDR=ip or f"10.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}.7")


def wrong(client, user, tenant):
    return login(client, user, host(tenant.slug), password="no-es-la-clave")


# --- Límite de intentos ------------------------------------------------------------------------


def test_too_many_failures_for_one_email_block_it_even_with_the_right_password(limits, tenant):
    user = UserFactory(tenant=tenant)
    client = client_from()
    for _ in range(3):
        assert wrong(client, user, tenant).status_code == 401

    blocked = login(client, user, host(tenant.slug))

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"
    # Otro correo desde otra IP sigue entrando: el bloqueo es solo de ese correo.
    other = UserFactory(tenant=tenant)
    assert login(client_from(), other, host(tenant.slug)).status_code == 200


def test_too_many_failures_from_one_ip_block_every_email(limits, tenant):
    client = client_from()
    users = [UserFactory(tenant=tenant) for _ in range(5)]
    for user in users:
        assert wrong(client, user, tenant).status_code == 401

    fresh = UserFactory(tenant=tenant)
    assert login(client, fresh, host(tenant.slug)).status_code == 429
    assert login(client_from(), fresh, host(tenant.slug)).status_code == 200


def test_a_successful_login_resets_the_email_counter(limits, tenant):
    user = UserFactory(tenant=tenant)
    client = client_from()
    for _ in range(2):
        wrong(client, user, tenant)
    assert login(client, user, host(tenant.slug)).status_code == 200
    for _ in range(2):
        assert wrong(client_from(), user, tenant).status_code == 401  # aún no llega a 3


def test_counters_are_per_business(limits, tenant):
    other = TenantFactory()
    user = UserFactory(tenant=tenant, email="misma@example.com")
    twin = UserFactory(tenant=other, email="misma@example.com")
    for _ in range(3):
        wrong(client_from(), user, tenant)
    assert login(client_from(), twin, host(other.slug)).status_code == 200


def test_password_reset_requests_are_limited(limits, tenant, mailoutbox):
    user = UserFactory(tenant=tenant)
    client = client_from()
    path = "/api/v1/auth/password-reset/"
    for _ in range(2):
        assert post(client, path, {"email": user.email}, host(tenant.slug)).status_code in (
            200,
            204,
        )
    response = post(client, path, {"email": user.email}, host(tenant.slug))
    assert response.status_code == 429
    assert len(mailoutbox) == 2


# --- Auditoría ---------------------------------------------------------------------------------


def actions():
    return list(AuditLog.objects.order_by("created_at").values_list("action", flat=True))


def test_logins_are_audited_without_secrets(tenant):
    user = UserFactory(tenant=tenant)
    client = client_from("203.0.113.9")
    wrong(client, user, tenant)
    post(
        client,
        "/api/v1/auth/login/",
        {"email": "nadie@example.com", "password": "x"},
        host(tenant.slug),
    )
    login(client, user, host(tenant.slug))

    assert actions() == ["auth.login_failed", "auth.login_failed", "auth.login"]
    failed, unknown, ok = AuditLog.objects.order_by("created_at")
    assert (failed.actor_id, failed.tenant_id, failed.ip) == (user.pk, tenant.pk, "203.0.113.9")
    assert (unknown.actor_id, unknown.entity_id, unknown.after) == (
        None,
        "",
        {"email": "nadie@example.com"},
    )
    assert unknown.tenant_id == tenant.pk
    assert ok.actor_id == user.pk
    assert "no-es-la-clave" not in json.dumps([row.after for row in (failed, unknown, ok)])


def test_password_change_and_two_factor_reset_are_audited(tenant):
    user = UserFactory(tenant=tenant)
    client = client_from()
    login(client, user, host(tenant.slug))
    response = post(
        client,
        "/api/v1/auth/password-change/",
        {"current_password": PASSWORD, "new_password": "Otra-Clave-Segura-2027!"},
        host(tenant.slug),
    )
    assert response.status_code in (200, 204), response.content

    accounts.reset_two_factor(user)

    assert actions()[-2:] == ["auth.password_change", "auth.two_factor_reset"]
    reset = AuditLog.objects.get(action="auth.two_factor_reset")
    assert (reset.actor_id, reset.ip) == (user.pk, None)


# --- Identificador de petición y logs ----------------------------------------------------------


def test_every_response_has_a_request_id():
    client = APIClient()
    generated = client.get("/healthz/")
    assert len(generated["X-Request-ID"]) == 32

    kept = client.get("/healthz/", HTTP_X_REQUEST_ID="proxy-1234abcd")
    assert kept["X-Request-ID"] == "proxy-1234abcd"

    replaced = client.get("/healthz/", HTTP_X_REQUEST_ID="<script>")
    assert replaced["X-Request-ID"] != "<script>"


def test_log_lines_carry_the_request_and_the_tenant(tenant):
    from config.request_id import _request_id

    record = logging.LogRecord("apps.test", logging.INFO, __file__, 1, "hola", None, None)
    token = _request_id.set("req-abc12345")
    try:
        with tenant_context(tenant):
            line = json.loads(JsonFormatter().format(record))
    finally:
        _request_id.reset(token)
    assert (line["request_id"], line["tenant"], line["message"]) == (
        "req-abc12345",
        tenant.slug,
        "hola",
    )
    assert "request_id" not in json.loads(JsonFormatter().format(record))
