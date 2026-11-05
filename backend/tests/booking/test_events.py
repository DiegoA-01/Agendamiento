"""Eventos en tiempo real (M7). Criterio de aceptación (spec §14): una cita creada en la web
aparece en la agenda abierta sin recargar; aquí, el evento llega al flujo SSE de la agenda."""

import functools
import json
from unittest import mock

import pytest
from django.db import transaction
from rest_framework.test import APIClient

from apps.booking import events
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import host, login

from .test_appointments_api import URL, Shop, at
from .test_public_api import booking

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def short_stream(monkeypatch):
    """Que ningún flujo quede abierto si un evento no llega: la prueba falla en vez de colgarse."""
    monkeypatch.setattr(events, "stream", functools.partial(events.stream, max_seconds=5))


@pytest.fixture
def shop():
    return Shop()


def open_agenda(shop, client):
    response = client.get("/api/v1/events/", HTTP_ACCEPT="text/event-stream")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/event-stream"
    chunks = iter(response.streaming_content)
    assert next(chunks).decode().startswith("retry: ")  # ya está suscrito
    return chunks


def next_event(chunks) -> str:
    for chunk in chunks:
        text = chunk.decode()
        if text.startswith("event: "):
            return text
    raise AssertionError("El evento no llegó.")


def test_events_accept_the_browser_event_stream_header(shop):
    """EventSource envía este Accept: debe abrir el flujo sin recibir un 406."""
    staff, _ = shop.client()
    response = staff.get("/api/v1/events/", HTTP_ACCEPT="text/event-stream")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/event-stream"
    response.close()


def test_events_with_event_stream_accept_need_a_session(shop):
    """La cabecera de EventSource conserva el error de sesión en JSON."""
    anonymous = APIClient(HTTP_HOST=host(shop.tenant.slug))
    response = anonymous.get("/api/v1/events/", HTTP_ACCEPT="text/event-stream")
    assert response.status_code == 401
    assert json.loads(response.content)["code"] == "not_authenticated"


def test_a_web_booking_reaches_the_open_agenda(shop, django_capture_on_commit_callbacks):
    ana = shop.professional()
    staff, _ = shop.client("receptionist")
    agenda = open_agenda(shop, staff)

    with django_capture_on_commit_callbacks(execute=True):
        web = APIClient(HTTP_HOST=host(shop.tenant.slug), REMOTE_ADDR="203.0.113.9")
        created = web.post("/api/v1/public/appointments/", booking(shop, at(9), ana), format="json")
    assert created.status_code == 201

    event = next_event(agenda)
    assert event.startswith("event: appointment.created\n")
    assert f'"professional_id": "{ana.pk}"' in event
    assert f'"start_at": "{at(9).isoformat()}"' in event


def test_status_changes_and_cancellations_are_announced(shop, django_capture_on_commit_callbacks):
    ana = shop.professional()
    staff, _ = shop.client()
    with django_capture_on_commit_callbacks(execute=True):
        appointment_id = staff.post(URL, shop.payload(at(9), ana), format="json").json()["id"]
    agenda = open_agenda(shop, staff)

    with django_capture_on_commit_callbacks(execute=True):
        staff.post(f"{URL}{appointment_id}/start/")
    assert next_event(agenda).startswith("event: appointment.updated\n")

    with django_capture_on_commit_callbacks(execute=True):
        other = staff.post(URL, shop.payload(at(10), ana), format="json").json()["id"]
        staff.post(f"{URL}{other}/cancel/")
    assert next_event(agenda).startswith("event: appointment.created\n")
    cancelled = next_event(agenda)
    assert cancelled.startswith("event: appointment.cancelled\n")
    assert '"status": "cancelled"' in cancelled


def test_a_professional_only_hears_about_their_own_appointments(
    shop, django_capture_on_commit_callbacks
):
    pro_user = UserFactory(tenant=shop.tenant, role="professional")
    ana = shop.professional("Ana", user=pro_user)
    beto = shop.professional("Beto")
    staff, _ = shop.client()
    pro = APIClient()
    login(pro, pro_user, host(shop.tenant.slug))
    pro.defaults["HTTP_HOST"] = host(shop.tenant.slug)
    agenda = open_agenda(shop, pro)

    with django_capture_on_commit_callbacks(execute=True):
        staff.post(URL, shop.payload(at(9), beto), format="json")
        staff.post(URL, shop.payload(at(9), ana), format="json")

    assert f'"professional_id": "{ana.pk}"' in next_event(agenda)


def test_nothing_is_published_if_the_transaction_rolls_back(shop):
    ana = shop.professional()
    staff, _ = shop.client()
    with mock.patch.object(events, "publish") as publish:
        with pytest.raises(RuntimeError), transaction.atomic():
            staff.post(URL, shop.payload(at(9), ana), format="json")
            raise RuntimeError("se deshace")
    publish.assert_not_called()


def test_events_need_a_session_and_the_booking_module(shop):
    from apps.tenancy import services as tenancy

    anonymous = APIClient(HTTP_HOST=host(shop.tenant.slug))
    assert anonymous.get("/api/v1/events/").status_code == 401
    staff, _ = shop.client()
    tenancy.set_modules(shop.tenant, {"booking": False})
    assert staff.get("/api/v1/events/").status_code == 403


def test_without_redis_the_appointment_is_still_saved(shop, django_capture_on_commit_callbacks):
    ana = shop.professional()
    staff, _ = shop.client()
    broken = mock.MagicMock()
    broken.publish.side_effect = events.redis.ConnectionError("Redis caído")
    with mock.patch.object(events, "_client", return_value=broken):
        with django_capture_on_commit_callbacks(execute=True):
            response = staff.post(URL, shop.payload(at(9), ana), format="json")
    assert response.status_code == 201
