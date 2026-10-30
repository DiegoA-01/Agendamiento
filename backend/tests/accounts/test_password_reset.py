import re

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from tests.factories import PASSWORD, SuperadminFactory, TenantFactory, UserFactory

from .helpers import ADMIN_HOST, host, login, post

pytestmark = pytest.mark.django_db

NEW_PASSWORD = "Nueva-Clave-Muy-Larga-2026!"


@pytest.fixture
def camila():
    return UserFactory(
        tenant=TenantFactory(slug="elfilo"), email="camila@x.com", full_name="Camila"
    )


def ask_reset(email: str, at: str):
    return post(APIClient(), "/api/v1/auth/password-reset/", {"email": email}, at)


def link_params() -> dict[str, str]:
    body = mail.outbox[-1].body
    match = re.search(r"uid=([^&\s]+)&token=([^&\s]+)", body)
    assert match, body
    return {"uid": match.group(1), "token": match.group(2)}


def confirm(params: dict, password: str, at: str):
    return post(
        APIClient(),
        "/api/v1/auth/password-reset/confirm/",
        {**params, "new_password": password},
        at,
    )


def test_existing_email_gets_one_email_with_a_link_to_the_tenant_host(camila):
    response = ask_reset("CAMILA@x.com", host("elfilo"))
    assert response.status_code == 204
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["camila@x.com"]
    assert f"{host('elfilo')}/recuperar/confirmar?uid=" in message.body
    assert "Camila" in message.body
    assert "contraseña" in message.subject.lower()


def test_unknown_email_gets_same_answer_and_no_email(camila):
    response = ask_reset("nadie@x.com", host("elfilo"))
    assert response.status_code == 204
    assert mail.outbox == []


def test_email_from_another_tenant_gets_no_email(camila):
    TenantFactory(slug="aura")
    assert ask_reset("camila@x.com", host("aura")).status_code == 204
    assert mail.outbox == []


def test_inactive_user_gets_no_email(camila):
    User.objects.filter(pk=camila.pk).update(is_active=False)
    ask_reset("camila@x.com", host("elfilo"))
    assert mail.outbox == []


def test_email_language_follows_the_tenant():
    tenant = TenantFactory(slug="spa-en", language="en")
    UserFactory(tenant=tenant, email="ann@x.com")
    ask_reset("ann@x.com", host("spa-en"))
    assert mail.outbox[0].subject == "Reset your password"


def test_reset_flow_changes_the_password(camila):
    ask_reset("camila@x.com", host("elfilo"))
    assert confirm(link_params(), NEW_PASSWORD, host("elfilo")).status_code == 204
    assert login(APIClient(), camila, host("elfilo")).status_code == 401
    assert login(APIClient(), camila, host("elfilo"), password=NEW_PASSWORD).status_code == 200


def test_link_works_only_once(camila):
    ask_reset("camila@x.com", host("elfilo"))
    params = link_params()
    assert confirm(params, NEW_PASSWORD, host("elfilo")).status_code == 204
    again = confirm(params, "Otra-Clave-Distinta-2026!", host("elfilo"))
    assert again.status_code == 400
    assert again.json()["code"] == "invalid_reset_token"


def test_weak_password_is_rejected_and_link_stays_valid(camila):
    ask_reset("camila@x.com", host("elfilo"))
    params = link_params()
    weak = confirm(params, "12345678", host("elfilo"))
    assert weak.status_code == 400
    assert weak.json()["code"] == "weak_password"
    assert weak.json()["fields"]["new_password"]
    assert confirm(params, NEW_PASSWORD, host("elfilo")).status_code == 204


@pytest.mark.parametrize("uid", ["basura", "", "AAAA"])
def test_garbage_uid_is_rejected(camila, uid):
    response = confirm({"uid": uid or "x", "token": "abc-def"}, NEW_PASSWORD, host("elfilo"))
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_reset_token"


def test_link_does_not_work_on_another_tenants_host(camila):
    TenantFactory(slug="aura")
    ask_reset("camila@x.com", host("elfilo"))
    response = confirm(link_params(), NEW_PASSWORD, host("aura"))
    assert response.status_code == 400
    assert login(APIClient(), camila, host("elfilo")).status_code == 200


def test_deleted_user_cannot_use_a_link_issued_before(camila):
    ask_reset("camila@x.com", host("elfilo"))
    params = link_params()
    User.objects.filter(pk=camila.pk).update(deleted_at=timezone.now())
    assert confirm(params, NEW_PASSWORD, host("elfilo")).status_code == 400


def test_superadmin_reset_works_on_the_admin_host():
    root = SuperadminFactory(email="root@x.com")
    ask_reset("root@x.com", ADMIN_HOST)
    assert confirm(link_params(), NEW_PASSWORD, ADMIN_HOST).status_code == 204
    root.refresh_from_db()
    assert root.check_password(NEW_PASSWORD)
    assert root.check_password(PASSWORD) is False
