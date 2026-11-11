"""S6: resumen del estado de la plataforma para el Super Admin."""

import datetime as dt

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.tenancy import services as tenancy
from apps.tenancy.models import Tenant
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import host
from tests.tenancy.factories import PlanFactory, TenantFactory

from .conftest import call

pytestmark = pytest.mark.django_db

URL = "/api/v1/platform/summary/"


def created(tenant, days_ago):
    Tenant.objects.filter(pk=tenant.pk).update(
        created_at=timezone.now() - dt.timedelta(days=days_ago)
    )


def test_counts_status_new_plans_and_verticals(api):
    basic, pro = PlanFactory(name="Básico"), PlanFactory(name="Pro")
    old = TenantFactory(plan=basic, vertical="barbershop")
    created(old, 90)
    edge = TenantFactory(plan=basic, vertical="salon")
    created(edge, 29)
    suspended = TenantFactory(plan=pro, vertical="barbershop", status=Tenant.Status.SUSPENDED)
    created(suspended, 40)
    newest = TenantFactory(plan=basic, vertical="barbershop")
    deleted = TenantFactory(plan=pro)
    tenancy.soft_delete_tenant(deleted)

    response = call(api, "get", URL)

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["window_days"] == 30
    assert (body["total"], body["active"], body["suspended"], body["new_recent"]) == (4, 3, 1, 2)
    assert body["by_plan"] == [
        {"plan_id": str(basic.pk), "name": "Básico", "count": 3},
        {"plan_id": str(pro.pk), "name": "Pro", "count": 1},
    ]
    assert body["by_vertical"] == [
        {"vertical": "barbershop", "count": 3},
        {"vertical": "salon", "count": 1},
    ]
    assert [tenant["id"] for tenant in body["latest"]] == [
        str(newest.pk),
        str(edge.pk),
        str(suspended.pk),
        str(old.pk),
    ]


def test_latest_shows_only_five(api):
    for _ in range(7):
        TenantFactory()
    assert len(call(api, "get", URL).json()["latest"]) == 5


def test_an_empty_platform_is_all_zero(api):
    body = call(api, "get", URL).json()
    assert (body["total"], body["active"], body["suspended"], body["new_recent"]) == (0, 0, 0, 0)
    assert body["by_plan"] == body["by_vertical"] == body["latest"] == []


def test_only_the_superadmin_sees_the_summary():
    shop = TenantFactory(slug="elfilo")
    assert call(APIClient(), "get", URL).status_code in (401, 403)

    owner = UserFactory(tenant=shop)
    client = APIClient()
    client.force_login(owner)
    assert call(client, "get", URL).status_code in (401, 403, 404)
    assert call(client, "get", URL, host=host("elfilo")).status_code in (401, 403, 404)
