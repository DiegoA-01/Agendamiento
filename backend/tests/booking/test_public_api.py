import datetime as dt
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.booking.models import Appointment
from apps.company import services as company
from apps.tenancy import services as tenancy
from apps.tenancy.context import tenant_context
from tests.accounts.helpers import ADMIN_HOST, host

from .test_appointments_api import Shop, at

pytestmark = pytest.mark.django_db

PUBLIC = "/api/v1/public"


@pytest.fixture
def shop():
    shop = Shop()
    company.create_company(shop.tenant, trade_name="Barbería El Filo")
    return shop


def visitor(shop, ip="203.0.113.7"):
    """Cliente sin sesión, como un celular entrando a elfilo.<dominio>/reservar."""
    client = APIClient(HTTP_HOST=host(shop.tenant.slug), REMOTE_ADDR=ip)
    return client


def booking(shop, start, professional=None, phone="300 123 4567", **extra):
    return {
        "service_ids": [str(shop.service.pk)],
        "professional_id": str(professional.pk) if professional else None,
        "start_at": start.isoformat(),
        "customer": {"full_name": "Camila Ríos", "phone": phone, "email": "camila@example.com"},
        "accept_data_policy": True,
        **extra,
    }


def book(client, shop, start, professional=None, **extra):
    return client.post(
        f"{PUBLIC}/appointments/", booking(shop, start, professional, **extra), format="json"
    )


# --- Información del negocio -------------------------------------------------------------------


def test_company_info_is_public_and_has_no_private_data(shop):
    response = visitor(shop).get(f"{PUBLIC}/company/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Barbería El Filo"
    assert body["booking_enabled"] is True
    assert body["cancel_min_hours"] == 2
    assert {"theme", "terms_html", "privacy_html", "cookies_html", "logo"} <= set(body)
    assert "tax_id" not in body and "legal_name" not in body


def test_services_are_grouped_by_category_and_only_active(shop):
    with tenant_context(shop.tenant):
        from tests.catalog.factories import ServiceFactory

        ServiceFactory(category=shop.service.category, name="Inactivo", is_active=False)

    body = visitor(shop).get(f"{PUBLIC}/services/").json()

    assert len(body) == 1
    assert [s["name"] for s in body[0]["services"]] == [shop.service.name]
    assert body[0]["services"][0]["price"] == "30000.00"


def test_professionals_only_those_with_online_booking(shop):
    ana = shop.professional("Ana")
    hidden = shop.professional("Beto")
    with tenant_context(shop.tenant):
        hidden.accepts_online_booking = False
        hidden.save()

    body = (
        visitor(shop)
        .get(f"{PUBLIC}/professionals/", {"service_ids": [str(shop.service.pk)]})
        .json()
    )

    assert [p["display_name"] for p in body] == ["Ana"]
    assert set(body[0]) == {"id", "display_name", "bio", "photo"}
    assert body[0]["id"] == str(ana.pk)


def test_public_slots_hide_who_attends_when_any_professional(shop):
    shop.professional("Ana")
    params = {"service_ids": [str(shop.service.pk)], "date": at(9).date().isoformat()}

    slots = visitor(shop).get(f"{PUBLIC}/availability/slots/", params).json()

    assert slots[0]["start"] == at(9).isoformat()
    assert slots[0]["professional_ids"] == []
    month = {"service_ids": [str(shop.service.pk)], "month": at(9).strftime("%Y-%m")}
    days = visitor(shop).get(f"{PUBLIC}/availability/days/", month).json()["days"]
    assert at(9).date().isoformat() in days


# --- Reservar ----------------------------------------------------------------------------------


def test_booking_from_the_web_creates_a_confirmed_web_appointment(shop):
    shop.professional("Ana")

    response = book(visitor(shop), shop, at(9))

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["professional"] == "Ana"
    assert body["customer_name"] == "Camila Ríos"
    assert body["items"] == [{"name": shop.service.name, "duration_min": 30, "price": "30000.00"}]
    assert body["can_cancel"] is True
    assert body["manage_url"].startswith(f"http://{host(shop.tenant.slug)}/cita/")
    with tenant_context(shop.tenant):
        appointment = Appointment.objects.get()
        assert appointment.source == "web"
        assert appointment.created_by is None
        assert appointment.customer.phone == "+573001234567"
        assert appointment.customer.data_consent_at is not None


def test_booking_requires_accepting_the_data_policy(shop):
    shop.professional()
    response = book(visitor(shop), shop, at(9), accept_data_policy=False)
    assert response.status_code == 400
    assert "accept_data_policy" in response.json()["fields"]


def test_the_honeypot_rejects_bots(shop):
    shop.professional()
    response = book(visitor(shop), shop, at(9), website="http://spam.example")
    assert response.status_code == 400
    with tenant_context(shop.tenant):
        assert not Appointment.objects.exists()


def test_a_taken_slot_returns_409_with_suggestions(shop):
    ana = shop.professional()
    assert book(visitor(shop), shop, at(9), ana).status_code == 201
    response = book(visitor(shop, "198.51.100.1"), shop, at(9), ana, phone="300 765 4321")
    assert response.status_code == 409
    assert response.json()["fields"]["suggestions"]


def test_public_booking_respects_the_minimum_notice(shop):
    ana = shop.professional()
    with tenant_context(shop.tenant):
        tenancy.update_agenda_settings(shop.tenant, min_notice_min=60 * 24 * 7)
    shop.tenant.refresh_from_db()
    assert book(visitor(shop), shop, at(9), ana).status_code == 409


# --- Límites (spec §9) ------------------------------------------------------------------------


def test_ten_posts_per_hour_per_ip(shop, settings):
    shop.professional()
    client = visitor(shop, "192.0.2.10")
    statuses = [
        book(client, shop, at(9), phone=f"300 000 00{i:02d}").status_code for i in range(11)
    ]
    assert statuses[0] == 201
    assert statuses[-1] == 429
    assert book(client, shop, at(10), phone="300 999 9999").json()["code"] == "rate_limited"
    # Otra IP no comparte el contador.
    assert book(visitor(shop, "192.0.2.11"), shop, at(10), phone="301 000 0000").status_code == 201


def test_five_posts_per_hour_per_phone(shop):
    shop.professional()
    results = [
        book(visitor(shop, f"192.0.2.{i}"), shop, at(9 + i % 3), phone="300 555 0000").status_code
        for i in range(6)
    ]
    assert results[-1] == 429


def test_the_client_ip_comes_from_the_trusted_proxy_header(shop, settings):
    shop.professional()
    settings.PUBLIC_BOOKING_LIMIT_PER_IP = 1
    proxy = "172.18.0.5"  # Caddy
    first = APIClient(
        HTTP_HOST=host(shop.tenant.slug),
        REMOTE_ADDR=proxy,
        HTTP_X_FORWARDED_FOR="203.0.113.50",
    )
    second = APIClient(
        HTTP_HOST=host(shop.tenant.slug),
        REMOTE_ADDR=proxy,
        HTTP_X_FORWARDED_FOR="203.0.113.51",
    )
    assert book(first, shop, at(9), phone="300 111 1111").status_code == 201
    # Detrás del mismo proxy, otra persona no queda bloqueada por la primera.
    assert book(second, shop, at(10), phone="300 222 2222").status_code == 201
    # Un cliente que antepone una IP falsa no se salta el límite: cuenta la que agregó Caddy.
    spoof = APIClient(
        HTTP_HOST=host(shop.tenant.slug),
        REMOTE_ADDR=proxy,
        HTTP_X_FORWARDED_FOR="10.0.0.1, 203.0.113.50",
    )
    assert book(spoof, shop, at(11), phone="300 333 3333").status_code == 429


def test_captcha_is_checked_when_enabled(shop, settings):
    shop.professional()
    settings.PUBLIC_BOOKING_CAPTCHA = True
    assert book(visitor(shop), shop, at(9)).json()["code"] == "captcha_required"

    reply = mock.MagicMock()
    reply.__enter__.return_value.read.return_value = b'{"success": false}'
    with mock.patch("urllib.request.urlopen", return_value=reply):
        assert book(visitor(shop), shop, at(9), captcha_token="x").json()["code"] == (
            "captcha_failed"
        )
    reply.__enter__.return_value.read.return_value = b'{"success": true}'
    with mock.patch("urllib.request.urlopen", return_value=reply):
        assert book(visitor(shop), shop, at(9), captcha_token="ok").status_code == 201


# --- Gestionar por enlace ---------------------------------------------------------------------


def token_from(response):
    return response.json()["manage_url"].rsplit("/", 1)[-1]


def test_see_and_cancel_by_token_frees_the_slot(shop):
    ana = shop.professional()
    client = visitor(shop)
    token = token_from(book(client, shop, at(9), ana))

    seen = client.get(f"{PUBLIC}/appointments/{token}/").json()
    assert seen["status"] == "confirmed" and seen["can_cancel"] is True

    cancelled = client.post(f"{PUBLIC}/appointments/{token}/cancel/", {"reason": "Viaje"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.post(f"{PUBLIC}/appointments/{token}/cancel/").status_code == 409
    assert (
        book(visitor(shop, "198.51.100.9"), shop, at(9), ana, phone="300 765 0000").status_code
        == 201
    )


def test_cancel_respects_the_business_window(shop):
    ana = shop.professional()
    token = token_from(book(visitor(shop), shop, at(9), ana))
    too_late = at(9) - dt.timedelta(hours=1)  # la ventana es de 2 h

    with mock.patch("django.utils.timezone.now", return_value=too_late):
        seen = visitor(shop).get(f"{PUBLIC}/appointments/{token}/").json()
        response = visitor(shop).post(f"{PUBLIC}/appointments/{token}/cancel/")

    assert seen["can_cancel"] is False
    assert response.status_code == 409
    assert response.json()["code"] == "cancel_window_closed"


def test_an_unknown_token_or_one_from_another_business_is_404(shop):
    ana = shop.professional()
    token = token_from(book(visitor(shop), shop, at(9), ana))
    other = Shop()
    assert visitor(shop).get(f"{PUBLIC}/appointments/no-existe/").status_code == 404
    assert visitor(other).get(f"{PUBLIC}/appointments/{token}/").status_code == 404
    assert visitor(other).post(f"{PUBLIC}/appointments/{token}/cancel/").status_code == 404


# --- Negocio y módulo -------------------------------------------------------------------------


def test_without_the_booking_module_only_the_company_page_answers(shop):
    tenancy.set_modules(shop.tenant, {"booking": False})
    client = visitor(shop)
    assert client.get(f"{PUBLIC}/company/").json()["booking_enabled"] is False
    assert client.get(f"{PUBLIC}/services/").json()["code"] == "module_disabled"


def test_public_endpoints_do_not_exist_on_the_platform_host():
    assert APIClient().get(f"{PUBLIC}/company/", HTTP_HOST=ADMIN_HOST).status_code == 404
