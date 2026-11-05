"""Tareas de Celery con el negocio activo (M8). Una tarea de un negocio nunca ve datos de otro, y
el worker no arrastra el negocio de una tarea a la siguiente."""

from unittest import mock

import pytest
from celery import shared_task
from django.db import connection, transaction

from apps.company.models import Location
from apps.tenancy import services as tenancy
from apps.tenancy import tasks
from apps.tenancy.context import get_current_tenant, tenant_context
from config.celery import app
from tests.company.factories import LocationFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db

seen: list[dict] = []


@shared_task(base=tasks.TenantTask, name="tests.tenancy.read_locations")
def read_locations(tenant_id, label=""):
    """Lo que vería una tarea real: el ORM (filtrado por negocio) y SQL directo (solo RLS)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM company_location")
        raw = cursor.fetchone()[0]
    seen.append(
        {
            "tenant": get_current_tenant(),
            "orm": sorted(Location.objects.values_list("name", flat=True)),
            "raw": raw,
            "label": label,
        }
    )
    return len(seen)


@shared_task(base=tasks.TenantTask, name="tests.tenancy.fails")
def fails(tenant_id):
    raise RuntimeError("falla la tarea")


@pytest.fixture(autouse=True)
def eager(monkeypatch):
    monkeypatch.setattr(app.conf, "task_always_eager", True)
    monkeypatch.setattr(app.conf, "task_eager_propagates", True)
    seen.clear()


@pytest.fixture
def two_businesses():
    alfa, beta = TenantFactory(), TenantFactory()
    LocationFactory(tenant=alfa, name="Sede Alfa")
    LocationFactory(tenant=beta, name="Sede Beta")
    return alfa, beta


def test_a_task_runs_inside_its_business_only(two_businesses):
    alfa, _ = two_businesses

    read_locations.delay(str(alfa.pk), "alfa")

    assert seen[0]["tenant"] == alfa
    assert seen[0]["orm"] == ["Sede Alfa"]
    assert seen[0]["raw"] == 1  # RLS también filtra el SQL directo
    assert get_current_tenant() is None  # al terminar, el worker queda sin negocio


def test_consecutive_tasks_do_not_inherit_the_previous_business(two_businesses):
    alfa, beta = two_businesses

    read_locations.delay(str(alfa.pk))
    read_locations.delay(str(beta.pk))

    assert [s["orm"] for s in seen] == [["Sede Alfa"], ["Sede Beta"]]


def test_the_previous_context_is_restored_after_a_nested_task(two_businesses):
    alfa, beta = two_businesses
    with tenant_context(alfa):
        read_locations.delay(str(beta.pk))
        assert get_current_tenant() == alfa
        assert list(Location.objects.values_list("name", flat=True)) == ["Sede Alfa"]
    assert seen[0]["orm"] == ["Sede Beta"]


def test_a_failing_task_still_releases_the_business(two_businesses):
    alfa, _ = two_businesses
    with pytest.raises(RuntimeError):
        fails.delay(str(alfa.pk))
    assert get_current_tenant() is None
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.current_tenant', true)")
        assert cursor.fetchone()[0] in ("", None)


def test_suspended_or_unknown_businesses_are_skipped(two_businesses):
    alfa, _ = two_businesses
    tenancy.suspend_tenant(alfa)

    assert read_locations.delay(str(alfa.pk)).get() is None
    assert read_locations.delay("00000000-0000-0000-0000-000000000000").get() is None
    assert seen == []


def test_delay_on_commit_waits_for_the_transaction(
    two_businesses, django_capture_on_commit_callbacks
):
    alfa, _ = two_businesses
    with mock.patch.object(read_locations, "delay") as delay:
        with pytest.raises(RuntimeError), transaction.atomic():
            tasks.delay_on_commit(read_locations, alfa, "deshecha")
            raise RuntimeError("rollback")
        delay.assert_not_called()

        with django_capture_on_commit_callbacks(execute=True):
            tasks.delay_on_commit(read_locations, alfa, "confirmada")
        delay.assert_called_once_with(str(alfa.pk), "confirmada")


def test_for_each_active_tenant_runs_once_per_active_business(two_businesses):
    alfa, beta = two_businesses
    suspended = TenantFactory()
    tenancy.suspend_tenant(suspended)

    queued = tasks.for_each_active_tenant.delay("tests.tenancy.read_locations", "beat").get()

    assert queued >= 2
    names = [s["orm"] for s in seen]
    assert ["Sede Alfa"] in names and ["Sede Beta"] in names
    assert all(s["tenant"].pk != suspended.pk for s in seen)
    assert all(s["label"] == "beat" for s in seen)


def test_for_each_active_tenant_only_accepts_tenant_tasks():
    with pytest.raises(ValueError):
        tasks.for_each_active_tenant.delay("tenancy.for_each_active_tenant").get()
