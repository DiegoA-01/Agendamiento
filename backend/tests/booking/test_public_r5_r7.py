"""R5 (especialidades en la reserva) y R7 (estado de cada día en el calendario)."""

import calendar
import datetime as dt

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.company import services as company
from apps.scheduling import availability
from apps.tenancy.context import tenant_context
from tests.booking.factories import AppointmentFactory
from tests.catalog.factories import SpecialtyFactory
from tests.scheduling.factories import TimeBlockFactory

from .test_appointments_api import BOGOTA, DAY, Shop
from .test_public_api import PUBLIC, visitor

pytestmark = pytest.mark.django_db


@pytest.fixture
def shop():
    shop = Shop()
    company.create_company(shop.tenant, trade_name="Barbería El Filo")
    return shop


def local(day: dt.date, hour: int, minute: int = 0) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hour, minute), tzinfo=BOGOTA)


# --- R5 ----------------------------------------------------------------------------------------


def test_public_professionals_show_their_specialties_by_name(shop):
    ana = shop.professional("Ana")
    beto = shop.professional("Beto")
    with tenant_context(shop.tenant):
        fade = SpecialtyFactory(name="Fade")
        beard = SpecialtyFactory(name="barba clásica")
        gone = SpecialtyFactory(name="Borrada")
        for specialty in (fade, beard, gone):
            ana.specialties.add(specialty, through_defaults={"tenant": shop.tenant})
        gone.deleted_at = dt.datetime.now(dt.UTC)
        gone.save()

    with CaptureQueriesContext(connection) as queries:
        body = (
            visitor(shop)
            .get(f"{PUBLIC}/professionals/", {"service_ids": [str(shop.service.pk)]})
            .json()
        )

    by_name = {p["display_name"]: p["specialties"] for p in body}
    assert by_name["Ana"] == [
        {"id": str(beard.pk), "name": "barba clásica"},
        {"id": str(fade.pk), "name": "Fade"},
    ]
    assert by_name["Beto"] == []
    assert str(beto.pk) in {p["id"] for p in body}
    specialty_queries = [q for q in queries.captured_queries if "catalog_specialty" in q["sql"]]
    assert len(specialty_queries) == 1  # una sola consulta para todas las fichas


# --- R7 ----------------------------------------------------------------------------------------


def status_of(shop, day, professional=None):
    with tenant_context(shop.tenant):
        services = availability.resolve_services([shop.service.pk])
        professionals = availability.candidates(
            services, professional.pk if professional else None, public=True
        )
        window = availability.booking_window(shop.tenant, public=True)
        return availability.day_status(shop.tenant, services, day, professionals, window=window)


def test_a_working_day_with_free_time_is_available(shop):
    shop.professional("Ana")
    assert status_of(shop, DAY) == "available"


def test_a_day_nobody_works_is_closed(shop):
    shop.professional("Ana")  # solo los lunes
    assert status_of(shop, DAY + dt.timedelta(days=1)) == "closed"


def test_a_working_day_without_free_slots_is_full(shop):
    ana = shop.professional("Ana")
    monday = DAY + dt.timedelta(days=7)
    with tenant_context(shop.tenant):
        for minutes in range(0, 180, 30):  # 9:00 a 12:00 en citas de 30 min
            start = local(monday, 9) + dt.timedelta(minutes=minutes)
            AppointmentFactory(
                professional=ana, start_at=start, end_at=start + dt.timedelta(minutes=30)
            )

    assert status_of(shop, monday) == "full"


def test_a_cancelled_appointment_frees_the_day_again(shop):
    ana = shop.professional("Ana")
    monday = DAY + dt.timedelta(days=7)
    with tenant_context(shop.tenant):
        for minutes in range(0, 180, 30):
            start = local(monday, 9) + dt.timedelta(minutes=minutes)
            AppointmentFactory(
                professional=ana,
                start_at=start,
                end_at=start + dt.timedelta(minutes=30),
                status="cancelled" if minutes == 60 else "confirmed",
            )

    assert status_of(shop, monday) == "available"


def test_a_day_blocked_for_everyone_is_closed_not_full(shop):
    ana = shop.professional("Ana")
    holiday = DAY + dt.timedelta(days=14)
    with tenant_context(shop.tenant):
        TimeBlockFactory(
            professional=ana, start_at=local(holiday, 0), end_at=local(holiday, 23, 59)
        )

    assert status_of(shop, holiday) == "closed"


def test_with_anyone_a_day_is_full_only_if_every_professional_is_full(shop):
    ana = shop.professional("Ana")
    beto = shop.professional("Beto")
    monday = DAY + dt.timedelta(days=7)
    with tenant_context(shop.tenant):
        TimeBlockFactory(professional=beto, start_at=local(monday, 0), end_at=local(monday, 23))
        for minutes in range(0, 180, 30):
            start = local(monday, 9) + dt.timedelta(minutes=minutes)
            AppointmentFactory(
                professional=ana, start_at=start, end_at=start + dt.timedelta(minutes=30)
            )

    assert status_of(shop, monday) == "full"  # Ana trabaja pero no tiene cupo; Beto no viene
    assert status_of(shop, monday, beto) == "closed"


def test_days_outside_the_booking_window_are_unavailable(shop):
    shop.professional("Ana")
    yesterday = dt.date.today() - dt.timedelta(days=1)
    too_far = DAY + dt.timedelta(days=7 * 10)  # lunes, pero más allá de los 60 días
    assert status_of(shop, yesterday) == "unavailable"
    assert status_of(shop, too_far) == "unavailable"


def test_days_endpoint_returns_every_day_of_the_month_with_its_status(shop):
    shop.professional("Ana")
    month = DAY.strftime("%Y-%m")

    response = visitor(shop).get(
        f"{PUBLIC}/availability/days/", {"service_ids": [str(shop.service.pk)], "month": month}
    )

    assert response.status_code == 200
    body = response.json()
    days_in_month = calendar.monthrange(DAY.year, DAY.month)[1]
    assert [d["date"] for d in body["calendar"]] == [
        dt.date(DAY.year, DAY.month, n).isoformat() for n in range(1, days_in_month + 1)
    ]
    statuses = {d["date"]: d["status"] for d in body["calendar"]}
    assert statuses[DAY.isoformat()] == "available"
    assert set(statuses.values()) <= {"available", "full", "closed", "unavailable"}
    # `days` sigue igual que antes: solo los disponibles.
    assert body["days"] == [d for d, s in statuses.items() if s == "available"]
    for date, status in statuses.items():
        if dt.date.fromisoformat(date).weekday() != 0 and status != "unavailable":
            assert status == "closed"


def test_the_dashboard_days_endpoint_has_the_calendar_too(shop):
    shop.professional("Ana")
    client, _ = shop.client()
    body = client.get(
        "/api/v1/availability/days/",
        {"service_ids": [str(shop.service.pk)], "month": DAY.strftime("%Y-%m")},
    ).json()
    assert {"days", "calendar"} == set(body)
