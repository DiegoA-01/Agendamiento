from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import ProfessionalService, Service
from apps.company import services as company
from apps.tenancy.context import tenant_context
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import host
from tests.catalog.factories import (
    ProfessionalFactory,
    ProfessionalServiceFactory,
    ResourceFactory,
    ServiceCategoryFactory,
    ServiceFactory,
)
from tests.company.factories import LocationFactory
from tests.media.factories import MediaFileFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant():
    tenant = TenantFactory()
    company.create_company(tenant)
    return tenant


def client_for(tenant, role="owner", user=None):
    client = APIClient()
    client.force_login(user or UserFactory(tenant=tenant, role=role))
    client.defaults["HTTP_HOST"] = host(tenant.slug)
    return client


def in_tenant(tenant, factory, **kwargs):
    with tenant_context(tenant):
        return factory(**kwargs)


# --- Permisos (matriz §5, `staff_services`) -----------------------------------------------------


@pytest.mark.parametrize(
    "role, can_view, can_write",
    [("owner", True, True), ("admin", True, True), ("receptionist", True, False),
     ("professional", True, False)],
)  # fmt: skip
@pytest.mark.parametrize("path", ["/api/v1/categories/", "/api/v1/services/"])
def test_catalog_permissions_by_role(tenant, role, can_view, can_write, path):
    client = client_for(tenant, role)
    assert client.get(path).status_code == (200 if can_view else 403)
    category = in_tenant(tenant, ServiceCategoryFactory)
    payload = (
        {"name": "Barba"}
        if "categories" in path
        else {
            "category_id": str(category.pk),
            "name": "Barba",
            "duration_min": 20,
            "price": "15000",
        }
    )
    assert client.post(path, payload, format="json").status_code == (201 if can_write else 403)


@pytest.mark.parametrize(
    "role, expected", [("owner", 200), ("admin", 200), ("receptionist", 200), ("professional", 403)]
)
def test_resources_are_not_shown_to_who_only_sees_their_own(tenant, role, expected):
    assert client_for(tenant, role).get("/api/v1/resources/").status_code == expected


def test_anonymous_gets_401(tenant):
    assert APIClient().get("/api/v1/services/", HTTP_HOST=host(tenant.slug)).status_code == 401


# --- Categorías ---------------------------------------------------------------------------------


def test_categories_are_listed_in_menu_order(tenant):
    client = client_for(tenant)
    client.post("/api/v1/categories/", {"name": "Uñas", "sort_order": 2}, format="json")
    client.post("/api/v1/categories/", {"name": "Cortes", "sort_order": 1}, format="json")
    assert [c["name"] for c in client.get("/api/v1/categories/").json()] == ["Cortes", "Uñas"]


def test_a_category_with_services_cannot_be_deleted(tenant):
    service = in_tenant(tenant, ServiceFactory)
    client = client_for(tenant)
    url = f"/api/v1/categories/{service.category_id}/"

    response = client.delete(url)
    assert response.status_code == 409
    assert response.json()["code"] == "category_in_use"

    assert client.delete(f"/api/v1/services/{service.pk}/").status_code == 204
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


# --- Servicios ----------------------------------------------------------------------------------


def test_owner_creates_and_edits_a_service(tenant):
    category = in_tenant(tenant, ServiceCategoryFactory)
    image = in_tenant(tenant, MediaFileFactory)
    client = client_for(tenant)

    response = client.post(
        "/api/v1/services/",
        {
            "category_id": str(category.pk),
            "name": "Corte clásico",
            "duration_min": 30,
            "buffer_min": 5,
            "price": "30000.50",
            "image_id": str(image.pk),
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["price"] == "30000.50"
    assert body["is_active"] is True
    assert body["image"]["id"] == str(image.pk)

    response = client.patch(
        f"/api/v1/services/{body['id']}/", {"price": "32000", "is_active": False}, format="json"
    )
    assert response.json()["price"] == "32000.00"
    with tenant_context(tenant):
        assert Service.objects.get(pk=body["id"]).price == Decimal("32000.00")
    assert client.get("/api/v1/services/?is_active=true").json() == []


@pytest.mark.parametrize(
    "field, value",
    [("duration_min", 0), ("price", "-1"), ("price", "12.345"), ("buffer_min", -5)],
)
def test_invalid_service_values_are_rejected(tenant, field, value):
    category = in_tenant(tenant, ServiceCategoryFactory)
    payload = {"category_id": str(category.pk), "name": "X", "duration_min": 30, "price": "1000"}
    payload[field] = value
    response = client_for(tenant).post("/api/v1/services/", payload, format="json")
    assert response.status_code == 400
    assert field in response.json()["fields"]


def test_a_service_cannot_use_a_category_or_image_of_another_business(tenant):
    other = TenantFactory()
    foreign_category = in_tenant(other, ServiceCategoryFactory)
    foreign_image = in_tenant(other, MediaFileFactory)
    category = in_tenant(tenant, ServiceCategoryFactory)
    client = client_for(tenant)
    base = {"name": "X", "duration_min": 30, "price": "1000"}

    response = client.post(
        "/api/v1/services/", {**base, "category_id": str(foreign_category.pk)}, format="json"
    )
    assert response.status_code == 400
    assert "category_id" in response.json()["fields"]

    response = client.post(
        "/api/v1/services/",
        {**base, "category_id": str(category.pk), "image_id": str(foreign_image.pk)},
        format="json",
    )
    assert response.status_code == 400
    assert "image_id" in response.json()["fields"]


def test_deleting_a_service_also_removes_it_from_every_professional(tenant):
    link = in_tenant(tenant, ProfessionalServiceFactory)
    client = client_for(tenant)

    assert client.delete(f"/api/v1/services/{link.service_id}/").status_code == 204

    with tenant_context(tenant):
        assert not ProfessionalService.objects.filter(pk=link.pk).exists()
        assert not Service.objects.filter(pk=link.service_id).exists()


def test_a_professional_only_sees_the_services_they_offer(tenant):
    user = UserFactory(tenant=tenant, role="professional")
    with tenant_context(tenant):
        professional = ProfessionalFactory(user=user)
        mine, other = ServiceFactory(name="Mío"), ServiceFactory(name="Ajeno")
        ProfessionalServiceFactory(professional=professional, service=mine)
    client = client_for(tenant, user=user)

    assert [s["name"] for s in client.get("/api/v1/services/").json()] == ["Mío"]
    assert client.get(f"/api/v1/services/{other.pk}/").status_code == 404
    assert [c["id"] for c in client.get("/api/v1/categories/").json()] == [str(mine.category_id)]


def test_a_professional_without_a_profile_sees_nothing(tenant):
    in_tenant(tenant, ServiceFactory)
    client = client_for(tenant, "professional")
    assert client.get("/api/v1/services/").json() == []


def test_services_can_be_filtered_by_category(tenant):
    with tenant_context(tenant):
        cut, nails = ServiceFactory(name="Corte"), ServiceFactory(name="Uñas")
    client = client_for(tenant)
    response = client.get(f"/api/v1/services/?category_id={cut.category_id}")
    assert [s["name"] for s in response.json()] == ["Corte"]
    assert client.get("/api/v1/services/?category_id=basura").json() == []
    assert nails


# --- Puestos ------------------------------------------------------------------------------------


def test_a_new_resource_goes_to_the_default_location(tenant):
    client = client_for(tenant)
    response = client.post(
        "/api/v1/resources/", {"name": "Silla 1", "kind": "silla"}, format="json"
    )

    assert response.status_code == 201
    assert response.json()["location_id"] == str(company.get_default_location(tenant).pk)


def test_a_resource_cannot_use_a_location_of_another_business(tenant):
    foreign = in_tenant(TenantFactory(), LocationFactory)
    response = client_for(tenant).post(
        "/api/v1/resources/", {"name": "Silla", "location_id": str(foreign.pk)}, format="json"
    )
    assert response.status_code == 400
    assert "location_id" in response.json()["fields"]


def test_resources_are_edited_and_soft_deleted(tenant):
    resource = in_tenant(tenant, ResourceFactory, name="Silla 1")
    client = client_for(tenant)
    url = f"/api/v1/resources/{resource.pk}/"

    assert client.patch(url, {"is_active": False}, format="json").json()["is_active"] is False
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


# --- Aislamiento entre negocios -----------------------------------------------------------------


@pytest.mark.parametrize(
    "factory, path",
    [
        (ServiceCategoryFactory, "categories"),
        (ServiceFactory, "services"),
        (ResourceFactory, "resources"),
    ],
)
def test_records_of_another_business_are_not_found(tenant, factory, path):
    foreign = in_tenant(TenantFactory(), factory)
    client = client_for(tenant)
    url = f"/api/v1/{path}/{foreign.pk}/"

    assert client.get(url).status_code == 404
    assert client.patch(url, {"name": "Mío"}, format="json").status_code == 404
    assert client.delete(url).status_code == 404
    assert client.get(f"/api/v1/{path}/").json() == []
    with tenant_context(foreign.tenant):
        assert type(foreign).objects.filter(pk=foreign.pk).exists()
