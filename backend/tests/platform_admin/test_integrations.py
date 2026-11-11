import datetime as dt
import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import NotificationLog
from apps.notifications.services import integration_summary, mask_recipient
from apps.platform_admin.services import tenant_integrations
from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_WHATSAPP
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import host
from tests.booking.factories import AppointmentFactory
from tests.notifications.factories import NotificationLogFactory
from tests.tenancy.factories import TenantFactory

from .conftest import call

pytestmark = pytest.mark.django_db


def url(tenant):
    return f"/api/v1/tenants/{tenant.pk}/integrations/"


def test_counts_window_last_sent_and_isolation(api):
    shop, other = TenantFactory(), TenantFactory()
    now = timezone.now()
    since = now - dt.timedelta(days=30)
    latest = now - dt.timedelta(hours=1)
    with tenancy.tenant_context(shop):
        appointment = AppointmentFactory()
        for channel in ("whatsapp", "email"):
            for status in ("sent", "failed", "queued"):
                NotificationLogFactory(
                    appointment=appointment,
                    channel=channel,
                    status=status,
                    sent_at=latest if status == "sent" else None,
                )
            boundary = NotificationLogFactory(
                appointment=appointment,
                channel=channel,
                status="sent",
                sent_at=now - dt.timedelta(days=2),
            )
            NotificationLog.objects.filter(pk=boundary.pk).update(created_at=since)
            old = NotificationLogFactory(
                appointment=appointment,
                channel=channel,
                status="sent",
                sent_at=now,
            )
            NotificationLog.objects.filter(pk=old.pk).update(
                created_at=since - dt.timedelta(seconds=1)
            )
    with tenancy.tenant_context(other):
        NotificationLogFactory(status="failed", error="otro negocio")
    summary = integration_summary(shop, since=since)
    assert [item["channel"] for item in summary["channels"]] == ["whatsapp", "email"]
    for item in summary["channels"]:
        assert (item["sent"], item["failed"], item["queued"]) == (2, 1, 1)
        assert item["last_sent_at"] == latest
    assert len(summary["recent_failures"]) == 2
    assert tenancy.get_current_tenant() is None
    response = call(api, "get", url(shop))
    assert response.status_code == 200, response.content
    assert response.json()["window_days"] == 30
    assert all(row["error"] != "otro negocio" for row in response.json()["recent_failures"])


def test_recent_failures_are_limited_ordered_masked_and_truncated(api):
    shop = TenantFactory()
    now = timezone.now()
    with tenancy.tenant_context(shop):
        appointment = AppointmentFactory()
        for index in range(7):
            log = NotificationLogFactory(
                appointment=appointment,
                status="failed",
                attempts=index,
                channel="whatsapp" if index % 2 else "email",
                to="+573001234567" if index % 2 else "camila@example.com",
                error="x" * 400,
            )
            NotificationLog.objects.filter(pk=log.pk).update(
                created_at=now - dt.timedelta(hours=index)
            )
        old = NotificationLogFactory(appointment=appointment, status="failed")
        NotificationLog.objects.filter(pk=old.pk).update(created_at=now - dt.timedelta(days=31))
    rows = call(api, "get", url(shop)).json()["recent_failures"]
    assert len(rows) == 5
    assert [row["attempts"] for row in rows] == list(range(5))
    assert [row["created_at"] for row in rows] == sorted(
        (row["created_at"] for row in rows), reverse=True
    )
    assert {row["to"] for row in rows} == {"c•••@example.com", "+57•••••4567"}
    assert all(row["error"] == "x" * 300 for row in rows)


@pytest.mark.parametrize(
    ("provider", "token", "phone", "expected", "configured"),
    [
        ("FakeProvider", "", "", "fake", True),
        ("CloudApiProvider", "token", "123", "cloud_api", True),
        ("CloudApiProvider", "", "123", "cloud_api", False),
        ("CloudApiProvider", "token", "", "cloud_api", False),
        ("CloudApiProvider", " ", "123", "cloud_api", False),
        ("CustomProvider", "token", "123", "other", False),
    ],
)
def test_provider_configuration(settings, provider, token, phone, expected, configured):
    settings.WHATSAPP_PROVIDER = f"apps.notifications.providers.{provider}"
    settings.WHATSAPP_TOKEN = token
    settings.WHATSAPP_PHONE_NUMBER_ID = phone
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    data = tenant_integrations(TenantFactory())
    assert data["whatsapp_provider"] == expected
    assert data["whatsapp_configured"] is configured
    assert data["email_backend"] == "locmem"


@pytest.mark.parametrize("enabled", [True, False])
def test_module_and_empty_business(api, enabled):
    shop = TenantFactory()
    tenancy.set_modules(shop, {MODULE_WHATSAPP: enabled})
    response = call(api, "get", url(shop))
    assert response.status_code == 200
    data = response.json()
    assert data["whatsapp_enabled"] is enabled
    assert data["recent_failures"] == []
    assert data["channels"] == [
        {"channel": channel, "sent": 0, "failed": 0, "queued": 0, "last_sent_at": None}
        for channel in ("whatsapp", "email")
    ]


def test_permissions_and_missing_business(api):
    shop = TenantFactory()
    path = url(shop)
    assert call(APIClient(), "get", path).status_code in (401, 403)
    owner = APIClient()
    owner.force_login(UserFactory(tenant=shop, role="owner"))
    assert call(owner, "get", path).status_code in (401, 403)
    assert call(owner, "get", path, host=host(shop.slug)).status_code in (401, 403)
    assert call(api, "get", path, host=host(shop.slug)).status_code in (401, 403)
    missing = call(api, "get", f"/api/v1/tenants/{uuid.uuid4()}/integrations/")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+573001234567", "+57•••••4567"),
        ("3001234567", "300•••••4567"),
        ("camila@example.com", "c•••@example.com"),
        ("a@example.com", "a•••@example.com"),
        ("", ""),
        ("12", "••"),
        ("1234567", "•••••••"),
        ("@", "•••@"),
    ],
)
def test_mask_recipient(value, expected):
    assert mask_recipient(value) == expected
