import pytest
from rest_framework.test import APIClient

from apps.booking.models import Customer
from apps.tenancy.context import tenant_context
from tests.accounts.helpers import host

from .test_appointments_api import URL as APPOINTMENTS
from .test_appointments_api import Shop, at

pytestmark = pytest.mark.django_db

URL = "/api/v1/customers/"


@pytest.fixture
def shop():
    return Shop()


def new_customer(client, **extra):
    data = {
        "full_name": "Camila Ríos",
        "phone": "300 123 4567",
        "email": "camila@example.com",
        "data_consent": True,
        **extra,
    }
    return client.post(URL, data, format="json")


@pytest.mark.parametrize("role", ["owner", "admin", "receptionist"])
def test_staff_creates_a_customer_with_consent(shop, role):
    client, _ = shop.client(role)

    response = new_customer(client, birthday="1995-04-12", notes="Prefiere a Ana")

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["phone"] == "+573001234567"
    assert body["birthday"] == "1995-04-12"
    assert body["appointments_count"] == 0
    assert body["data_consent_at"] is not None


def test_consent_is_required(shop):
    client, _ = shop.client()
    response = new_customer(client, data_consent=False)
    assert response.status_code == 400
    assert "data_consent" in response.json()["fields"]


def test_a_phone_belongs_to_one_customer(shop):
    client, _ = shop.client()
    new_customer(client)
    response = new_customer(client, full_name="Otra", phone="+57 300 123 4567")
    assert response.status_code == 409
    assert response.json()["code"] == "customer_exists"


def test_search_by_name_or_phone(shop):
    client, _ = shop.client()
    new_customer(client)
    new_customer(client, full_name="Juan Pérez", phone="311 999 8888")

    def names(q):
        return [c["full_name"] for c in client.get(URL, {"q": q}).json()["results"]]

    assert names("") == ["Camila Ríos", "Juan Pérez"]
    assert names("cami") == ["Camila Ríos"]
    assert names("311 999") == ["Juan Pérez"]


def test_counts_appointments_and_survives_soft_delete(shop):
    ana = shop.professional()
    client, _ = shop.client()
    customer_id = client.post(APPOINTMENTS, shop.payload(at(9), ana), format="json").json()[
        "customer"
    ]["id"]
    url = f"{URL}{customer_id}/"

    assert client.get(url).json()["appointments_count"] == 1
    assert client.patch(url, {"notes": "VIP"}, format="json").json()["notes"] == "VIP"
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    with tenant_context(shop.tenant):
        assert Customer.all_tenants.get(pk=customer_id).deleted_at is not None
    # La cita sigue ahí con su cliente.
    assert client.get(APPOINTMENTS).json()["results"][0]["customer"]["id"] == customer_id


def test_changing_the_phone_to_one_in_use_is_rejected(shop):
    client, _ = shop.client()
    first = new_customer(client).json()["id"]
    new_customer(client, full_name="Juan", phone="311 999 8888")
    response = client.patch(f"{URL}{first}/", {"phone": "3119998888"}, format="json")
    assert response.status_code == 409


def test_professionals_do_not_manage_customers(shop):
    client, _ = shop.client("professional")
    assert client.get(URL).status_code == 403
    assert new_customer(client).status_code == 403


def test_customers_of_another_business_are_invisible(shop):
    other = Shop()
    other_client, _ = other.client()
    foreign = new_customer(other_client).json()["id"]
    client, _ = shop.client()
    assert client.get(URL).json()["results"] == []
    assert client.get(f"{URL}{foreign}/").status_code == 404
    assert client.delete(f"{URL}{foreign}/").status_code == 404


def test_anonymous_cannot_list_customers(shop):
    assert APIClient(HTTP_HOST=host(shop.tenant.slug)).get(URL).status_code == 401
