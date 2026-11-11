"""R3: reglas para combinar servicios y un cliente no puede estar en dos citas a la vez."""

import pytest

from apps.booking.models import Appointment
from apps.company import services as company
from apps.tenancy.context import tenant_context
from tests.catalog.factories import (
    ProfessionalServiceFactory,
    ServiceCategoryFactory,
    ServiceFactory,
)

from .test_appointments_api import URL, Shop, at
from .test_public_api import PUBLIC, booking, visitor

pytestmark = pytest.mark.django_db


class RulesShop(Shop):
    """Cortes es "solo uno por cita"; Barba y Cejas no."""

    def __init__(self):
        super().__init__()
        company.create_company(self.tenant, trade_name="Barbería El Filo")
        with tenant_context(self.tenant):
            cuts = self.service.category
            cuts.name, cuts.single_choice = "Cortes", True
            cuts.save()
            self.fade = ServiceFactory(category=cuts, name="Fade", duration_min=30)
            extras = ServiceCategoryFactory(name="Barba y cejas")
            self.beard = ServiceFactory(category=extras, name="Barba", duration_min=15)
            self.brows = ServiceFactory(category=extras, name="Cejas", duration_min=15)

    def professional(self, name="Ana", user=None, **link):
        professional = super().professional(name, user, **link)
        with tenant_context(self.tenant):
            for service in (self.fade, self.beard, self.brows):
                ProfessionalServiceFactory(professional=professional, service=service)
        return professional


@pytest.fixture
def shop():
    return RulesShop()


def post_json(client, data):
    return client.post(URL, data, format="json")


def ids(*services):
    return [str(service.pk) for service in services]


# --- Un servicio por categoría -----------------------------------------------------------------


def test_two_cuts_in_one_appointment_are_rejected(shop):
    ana = shop.professional()
    client, _ = shop.client()

    response = post_json(client, shop.payload(at(9), ana, service_ids=ids(shop.service, shop.fade)))

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "one_per_category"
    assert "service_ids" in body["fields"]
    with tenant_context(shop.tenant):
        assert not Appointment.objects.exists()


def test_a_cut_plus_beard_and_brows_is_allowed(shop):
    ana = shop.professional()
    client, _ = shop.client()

    response = post_json(
        client, shop.payload(at(9), ana, service_ids=ids(shop.service, shop.beard, shop.brows))
    )

    assert response.status_code == 201, response.json()
    assert len(response.json()["items"]) == 3


def test_categories_without_the_rule_allow_several_services(shop):
    with tenant_context(shop.tenant):
        category = shop.service.category
        category.single_choice = False
        category.save()
    ana = shop.professional()
    client, _ = shop.client()

    response = post_json(client, shop.payload(at(9), ana, service_ids=ids(shop.service, shop.fade)))

    assert response.status_code == 201, response.json()


def test_the_public_booking_and_availability_apply_the_rule_too(shop):
    shop.professional()
    client = visitor(shop)

    slots = client.get(
        f"{PUBLIC}/availability/slots/",
        {"service_ids": ids(shop.service, shop.fade), "date": at(9).date().isoformat()},
    )
    assert slots.status_code == 400
    assert slots.json()["code"] == "one_per_category"

    response = client.post(
        f"{PUBLIC}/appointments/",
        {**booking(shop, at(9)), "service_ids": ids(shop.service, shop.fade)},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "one_per_category"


def test_public_services_say_which_categories_allow_only_one(shop):
    body = visitor(shop).get(f"{PUBLIC}/services/").json()
    rules = {category["name"]: category["single_choice"] for category in body}
    assert rules == {"Cortes": True, "Barba y cejas": False}


def test_owner_turns_the_rule_on_and_off_from_the_catalog(shop):
    client, _ = shop.client()
    category_id = shop.service.category_id

    response = client.patch(
        f"/api/v1/categories/{category_id}/", {"single_choice": False}, format="json"
    )
    assert response.status_code == 200, response.json()
    assert response.json()["single_choice"] is False

    created = client.post(
        "/api/v1/categories/", {"name": "Tintes", "single_choice": True}, format="json"
    )
    assert created.status_code == 201
    assert created.json()["single_choice"] is True


# --- El mismo cliente no puede estar en dos citas a la vez -------------------------------------


def test_the_same_customer_cannot_book_two_overlapping_appointments(shop):
    ana, beto = shop.professional("Ana"), shop.professional("Beto")
    client, _ = shop.client()
    assert post_json(client, shop.payload(at(9), ana)).status_code == 201

    # Mismo celular, otro profesional libre, horario que se cruza (9:15).
    response = post_json(client, shop.payload(at(9, 15), beto))

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "customer_overlap"
    assert body["fields"]["start_at"] == [at(9).isoformat()]
    with tenant_context(shop.tenant):
        assert Appointment.objects.count() == 1


def test_the_same_customer_can_book_back_to_back_or_another_day(shop):
    ana = shop.professional()
    client, _ = shop.client()
    assert post_json(client, shop.payload(at(9), ana)).status_code == 201
    assert post_json(client, shop.payload(at(9, 30), ana)).status_code == 201  # justo después


def test_another_customer_can_take_the_same_time_with_another_professional(shop):
    ana, beto = shop.professional("Ana"), shop.professional("Beto")
    client, _ = shop.client()
    assert post_json(client, shop.payload(at(9), ana)).status_code == 201

    other = shop.payload(at(9), beto)
    other["customer"] = {"full_name": "Pedro Gómez", "phone": "301 765 4321"}
    assert post_json(client, other).status_code == 201

    # Con el mismo profesional, en cambio, el horario ya está tomado.
    third = shop.payload(at(9), ana)
    third["customer"] = {"full_name": "Laura Díaz", "phone": "302 111 2233"}
    assert post_json(client, third).json()["code"] == "slot_taken"


def test_a_cancelled_appointment_does_not_block_the_customer(shop):
    ana = shop.professional()
    client, _ = shop.client()
    first = post_json(client, shop.payload(at(9), ana)).json()
    assert client.post(f"{URL}{first['id']}/cancel/", {}, format="json").status_code == 200

    assert post_json(client, shop.payload(at(9), ana)).status_code == 201


def test_the_public_booking_also_blocks_a_second_appointment_at_the_same_time(shop):
    shop.professional("Ana")
    shop.professional("Beto")
    client = visitor(shop)
    assert (
        client.post(f"{PUBLIC}/appointments/", booking(shop, at(9)), format="json").status_code
        == 201
    )

    again = client.post(f"{PUBLIC}/appointments/", booking(shop, at(9)), format="json")

    assert again.status_code == 409
    assert again.json()["code"] == "customer_overlap"
