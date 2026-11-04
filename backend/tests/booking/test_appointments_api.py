import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from rest_framework.test import APIClient

from apps.booking.models import Appointment, Customer
from apps.tenancy import services as tenancy
from apps.tenancy.context import tenant_context
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import host, login
from tests.booking.factories import AppointmentFactory, CustomerFactory
from tests.catalog.factories import (
    ProfessionalFactory,
    ProfessionalServiceFactory,
    ResourceFactory,
    ServiceFactory,
)
from tests.scheduling.factories import WorkingHoursFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db

BOGOTA = ZoneInfo("America/Bogota")
URL = "/api/v1/appointments/"


def next_monday() -> dt.date:
    today = dt.date.today()
    return today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)


DAY = next_monday()


def at(hour: int, minute: int = 0) -> dt.datetime:
    return dt.datetime.combine(DAY, dt.time(hour, minute), tzinfo=BOGOTA)


class Shop:
    """Un negocio listo para agendar: un servicio de 30 min y profesionales que lo ofrecen los
    lunes de 9 a 12."""

    def __init__(self):
        self.tenant = TenantFactory()
        with tenant_context(self.tenant):
            self.service = ServiceFactory(duration_min=30, price="30000.00")

    def professional(self, name="Ana", user=None, **link):
        with tenant_context(self.tenant):
            professional = ProfessionalFactory(display_name=name, user=user)
            ProfessionalServiceFactory(professional=professional, service=self.service, **link)
            WorkingHoursFactory(
                professional=professional,
                weekday=0,
                start_time=dt.time(9),
                end_time=dt.time(12),
            )
        return professional

    def client(self, role="owner"):
        user = UserFactory(tenant=self.tenant, role=role)
        client = APIClient()
        login(client, user, host(self.tenant.slug))
        client.defaults["HTTP_HOST"] = host(self.tenant.slug)
        return client, user

    def payload(self, start, professional=None, **extra):
        return {
            "service_ids": [str(self.service.pk)],
            "professional_id": str(professional.pk) if professional else None,
            "start_at": start.isoformat(),
            "customer": {"full_name": "Camila Ríos", "phone": "300 123 4567"},
            **extra,
        }


@pytest.fixture
def shop():
    return Shop()


def book(shop, client, start, professional=None, **extra):
    return client.post(URL, shop.payload(start, professional, **extra), format="json")


# --- Crear -------------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["owner", "admin", "receptionist"])
def test_staff_creates_a_confirmed_appointment_with_a_new_customer(shop, role):
    ana = shop.professional(price_override="45000.00")
    client, user = shop.client(role)

    response = book(shop, client, at(9), ana)

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["source"] == "dashboard"
    assert body["professional_id"] == str(ana.pk)
    assert body["start_at"] == at(9).isoformat()
    assert body["end_at"] == at(9, 30).isoformat()
    assert body["price_total"] == "45000.00"
    assert body["items"] == [
        {"service_id": str(shop.service.pk), "price_charged": "45000.00", "duration_min": 30}
    ]
    assert body["customer"]["phone"] == "+573001234567"
    with tenant_context(shop.tenant):
        appointment = Appointment.objects.get()
        assert appointment.created_by_id == user.pk
        assert appointment.items.get().commission_pct_snapshot == ana.default_commission_pct


def test_an_existing_customer_is_reused_by_phone_or_by_id(shop):
    ana = shop.professional()
    client, _ = shop.client()
    with tenant_context(shop.tenant):
        existing = CustomerFactory(phone="+573001234567", full_name="Camila")

    assert book(shop, client, at(9), ana).json()["customer"]["id"] == str(existing.pk)
    by_id = shop.payload(at(10), ana, customer=None, customer_id=str(existing.pk))
    assert client.post(URL, by_id, format="json").json()["customer"]["id"] == str(existing.pk)
    with tenant_context(shop.tenant):
        assert Customer.objects.count() == 1


def test_a_taken_slot_returns_409_with_suggestions(shop):
    ana = shop.professional()
    client, _ = shop.client()
    assert book(shop, client, at(9), ana).status_code == 201

    response = book(shop, client, at(9), ana)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "slot_taken"
    assert body["fields"]["suggestions"][0] == at(9, 30).isoformat()


def test_a_start_outside_the_grid_or_the_working_hours_is_not_bookable(shop):
    ana = shop.professional()
    client, _ = shop.client()
    assert book(shop, client, at(9, 7), ana).status_code == 409
    assert book(shop, client, at(13), ana).status_code == 409


def test_any_professional_goes_to_the_one_with_fewer_appointments_that_day(shop):
    ana, beto = shop.professional("Ana"), shop.professional("Beto")
    client, _ = shop.client()
    with tenant_context(shop.tenant):
        AppointmentFactory(professional=ana, start_at=at(11), end_at=at(11, 30))

    first = book(shop, client, at(9)).json()
    assert first["professional_id"] == str(beto.pk)
    # Empate (una cita cada uno): gana el orden alfabético.
    assert book(shop, client, at(10)).json()["professional_id"] == str(ana.pk)


def test_any_professional_falls_back_when_the_first_one_is_busy(shop):
    ana, beto = shop.professional("Ana"), shop.professional("Beto")
    client, _ = shop.client()
    assert book(shop, client, at(9), ana).status_code == 201
    assert book(shop, client, at(9)).json()["professional_id"] == str(beto.pk)
    assert book(shop, client, at(9)).status_code == 409


def test_a_service_that_needs_a_resource_gets_a_free_one(shop):
    ana = shop.professional()
    with tenant_context(shop.tenant):
        shop.service.requires_resource = True
        shop.service.save()
        chair = ResourceFactory(location=ana.location)
    client, _ = shop.client()

    assert book(shop, client, at(9), ana).json()["resource_id"] == str(chair.pk)


def test_invalid_payloads(shop):
    ana = shop.professional()
    client, _ = shop.client()
    no_customer = shop.payload(at(9), ana, customer=None)
    assert client.post(URL, no_customer, format="json").status_code == 400
    bad_phone = shop.payload(at(9), ana, customer={"full_name": "X", "phone": "12"})
    assert client.post(URL, bad_phone, format="json").json()["fields"] == {
        "phone": ["Usa un celular válido, por ejemplo 300 123 4567."]
    }
    unknown_service = shop.payload(at(9), ana, service_ids=[str(ana.pk)])
    assert client.post(URL, unknown_service, format="json").json()["code"] == "invalid_services"


# --- Estados (spec §7) --------------------------------------------------------------------------


def action(client, appointment_id, name, **data):
    return client.post(f"{URL}{appointment_id}/{name}/", data, format="json")


def test_the_full_happy_path_and_invalid_transitions(shop):
    ana = shop.professional()
    client, _ = shop.client()
    appointment_id = book(shop, client, at(9), ana).json()["id"]

    assert action(client, appointment_id, "confirm").json()["code"] == "invalid_transition"
    assert action(client, appointment_id, "complete").status_code == 409
    assert action(client, appointment_id, "start").json()["status"] == "in_progress"
    assert action(client, appointment_id, "cancel").status_code == 409
    assert action(client, appointment_id, "complete").json()["status"] == "completed"
    assert action(client, appointment_id, "no-show").status_code == 409


def test_cancel_records_the_reason_and_frees_the_slot(shop):
    ana = shop.professional()
    client, _ = shop.client()
    appointment_id = book(shop, client, at(9), ana).json()["id"]

    cancelled = action(client, appointment_id, "cancel", reason="Viaje").json()

    assert cancelled["status"] == "cancelled"
    assert cancelled["cancel_reason"] == "Viaje"
    assert cancelled["cancelled_at"] is not None
    assert book(shop, client, at(9), ana).status_code == 201


def test_no_show_frees_the_slot(shop):
    ana = shop.professional()
    client, _ = shop.client()
    appointment_id = book(shop, client, at(9), ana).json()["id"]
    assert action(client, appointment_id, "no-show").json()["status"] == "no_show"
    assert book(shop, client, at(9), ana).status_code == 201


def test_reschedule_creates_a_linked_appointment_and_can_overlap_the_old_time(shop):
    ana = shop.professional()
    client, _ = shop.client()
    original = book(shop, client, at(9), ana).json()["id"]

    moved = action(client, original, "reschedule", start_at=at(9, 15).isoformat())

    assert moved.status_code == 201, moved.json()
    assert moved.json()["rescheduled_from_id"] == original
    assert moved.json()["start_at"] == at(9, 15).isoformat()
    assert client.get(f"{URL}{original}/").json()["status"] == "rescheduled"


def test_reschedule_to_a_taken_slot_changes_nothing(shop):
    ana = shop.professional()
    client, _ = shop.client()
    original = book(shop, client, at(9), ana).json()["id"]
    assert book(shop, client, at(10), ana).status_code == 201

    response = action(client, original, "reschedule", start_at=at(10).isoformat())

    assert response.status_code == 409
    assert response.json()["code"] == "slot_taken"
    assert client.get(f"{URL}{original}/").json()["status"] == "confirmed"


def test_patch_assigns_a_resource_of_the_same_location(shop):
    ana = shop.professional()
    client, _ = shop.client()
    appointment_id = book(shop, client, at(9), ana).json()["id"]
    with tenant_context(shop.tenant):
        chair = ResourceFactory(location=ana.location)
        elsewhere = ResourceFactory()

    url = f"{URL}{appointment_id}/"
    assert client.patch(url, {"resource_id": str(chair.pk)}, format="json").json()[
        "resource_id"
    ] == str(chair.pk)
    assert client.patch(url, {"resource_id": str(elsewhere.pk)}, format="json").status_code == 400
    assert client.patch(url, {"resource_id": None}, format="json").json()["resource_id"] is None


# --- Listado, permisos y aislamiento -----------------------------------------------------------


def test_list_filters_by_range_professional_and_status(shop):
    ana, beto = shop.professional("Ana"), shop.professional("Beto")
    client, _ = shop.client()
    first = book(shop, client, at(9), ana).json()["id"]
    second = book(shop, client, at(11), beto).json()["id"]
    action(client, second, "cancel")

    def ids(**params):
        return [a["id"] for a in client.get(URL, params).json()["results"]]

    assert ids() == [first, second]
    assert ids(professional_id=ana.pk) == [first]
    assert ids(status="cancelled") == [second]
    assert ids(start_at=at(10).isoformat(), end_at=at(12).isoformat()) == [second]


def test_a_professional_sees_and_acts_only_on_their_own_appointments(shop):
    pro_user = UserFactory(tenant=shop.tenant, role="professional")
    ana = shop.professional("Ana", user=pro_user)
    beto = shop.professional("Beto")
    staff, _ = shop.client()
    mine = book(shop, staff, at(9), ana).json()["id"]
    theirs = book(shop, staff, at(9), beto).json()["id"]

    pro = APIClient()
    login(pro, pro_user, host(shop.tenant.slug))
    pro.defaults["HTTP_HOST"] = host(shop.tenant.slug)

    assert [a["id"] for a in pro.get(URL).json()["results"]] == [mine]
    assert pro.get(f"{URL}{theirs}/").status_code == 404
    assert action(pro, theirs, "no-show").status_code == 404
    assert book(shop, pro, at(10), ana).status_code == 403
    assert action(pro, mine, "cancel").status_code == 403
    action(staff, mine, "start")
    assert action(pro, mine, "complete").json()["status"] == "completed"


def test_appointments_of_another_business_are_not_found(shop):
    other = Shop()
    foreign_pro = other.professional()
    other_client, _ = other.client()
    foreign = book(other, other_client, at(9), foreign_pro).json()["id"]
    client, _ = shop.client()

    assert client.get(URL).json()["results"] == []
    assert client.get(f"{URL}{foreign}/").status_code == 404
    assert action(client, foreign, "cancel").status_code == 404


def test_without_the_booking_module_the_api_is_closed(shop):
    shop.professional()
    client, _ = shop.client()
    tenancy.set_modules(shop.tenant, {"booking": False})

    response = client.get(URL)
    assert response.status_code == 403
    assert response.json()["code"] == "module_disabled"
    assert client.get("/api/v1/availability/slots/").status_code == 403


# --- Disponibilidad en el panel ----------------------------------------------------------------


def test_availability_endpoints_for_the_dashboard(shop):
    ana = shop.professional()
    client, _ = shop.client("receptionist")
    params = {"service_ids": [str(shop.service.pk)], "date": DAY.isoformat()}

    slots = client.get("/api/v1/availability/slots/", params).json()
    assert slots[0] == {
        "start": at(9).isoformat(),
        "end": at(9, 30).isoformat(),
        "period": "morning",
        "professional_ids": [str(ana.pk)],
    }
    month = {"service_ids": [str(shop.service.pk)], "month": DAY.strftime("%Y-%m")}
    days = client.get("/api/v1/availability/days/", month).json()["days"]
    assert DAY.isoformat() in days

    pro_client, _ = shop.client("professional")
    assert pro_client.get("/api/v1/availability/slots/", params).status_code == 403
