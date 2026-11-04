import pytest
from rest_framework.test import APIClient

from apps.company import services as company
from apps.company.models import Location
from apps.tenancy.context import tenant_context
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import host
from tests.catalog.factories import ProfessionalFactory, ResourceFactory
from tests.media.factories import MediaFileFactory
from tests.tenancy.factories import PlanFactory, TenantFactory

pytestmark = pytest.mark.django_db

ROLES = ["owner", "admin", "receptionist", "professional"]


@pytest.fixture
def tenant():
    tenant = TenantFactory(plan=PlanFactory(max_locations=2))
    company.create_company(tenant, trade_name="Barbería El Filo")
    return tenant


def client_for(tenant, role="owner"):
    client = APIClient()
    client.force_login(UserFactory(tenant=tenant, role=role))
    client.defaults["HTTP_HOST"] = host(tenant.slug)
    return client


def default_location(tenant):
    return company.get_default_location(tenant)


# --- Permisos (matriz §5: el propietario edita, el administrador ve, los demás nada) -----------


@pytest.mark.parametrize(
    "role, can_view, can_edit",
    [("owner", True, True), ("admin", True, False), ("receptionist", False, False),
     ("professional", False, False)],
)  # fmt: skip
def test_company_and_locations_follow_the_permission_matrix(tenant, role, can_view, can_edit):
    client = client_for(tenant, role)
    location_url = f"/api/v1/locations/{default_location(tenant).pk}/"

    assert client.get("/api/v1/company/").status_code == (200 if can_view else 403)
    assert client.get("/api/v1/locations/").status_code == (200 if can_view else 403)
    assert client.get(location_url).status_code == (200 if can_view else 403)

    edit = 200 if can_edit else 403
    assert client.patch("/api/v1/company/", {"city": "Cali"}, format="json").status_code == edit
    assert client.patch(location_url, {"name": "Centro"}, format="json").status_code == edit
    created = client.post("/api/v1/locations/", {"name": "Norte"}, format="json")
    assert created.status_code == (201 if can_edit else 403)


def test_anonymous_gets_401(tenant):
    client = APIClient()
    assert client.get("/api/v1/company/", HTTP_HOST=host(tenant.slug)).status_code == 401


# --- Empresa ------------------------------------------------------------------------------------


def test_owner_reads_and_edits_the_company(tenant):
    client = client_for(tenant)
    response = client.patch(
        "/api/v1/company/",
        {
            "legal_name": "El Filo S.A.S.",
            "tax_id": "900123456-7",
            "social_links": {"instagram": "https://instagram.com/elfilo"},
            "terms_html": "<p>Llega <strong>10 minutos</strong> antes.</p><script>x()</script>",
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["trade_name"] == "Barbería El Filo"
    assert body["legal_name"] == "El Filo S.A.S."
    assert body["social_links"] == {"instagram": "https://instagram.com/elfilo"}
    # El HTML legal se guarda ya limpio: lo que se muestra al público no trae scripts.
    assert body["terms_html"] == "<p>Llega <strong>10 minutos</strong> antes.</p>"
    assert client.get("/api/v1/company/").json()["tax_id"] == "900123456-7"


def test_unknown_social_networks_are_rejected(tenant):
    response = client_for(tenant).patch(
        "/api/v1/company/", {"social_links": {"myspace": "https://myspace.com/x"}}, format="json"
    )
    assert response.status_code == 400
    assert "social_links" in response.json()["fields"]


def test_the_logo_is_an_image_of_the_same_business(tenant):
    client = client_for(tenant)
    with tenant_context(tenant):
        own = MediaFileFactory()
    with tenant_context(TenantFactory()):
        foreign = MediaFileFactory()

    response = client.patch("/api/v1/company/", {"logo_id": str(own.pk)}, format="json")
    assert response.status_code == 200
    assert response.json()["logo"]["id"] == str(own.pk)

    response = client.patch("/api/v1/company/", {"logo_id": str(foreign.pk)}, format="json")
    assert response.status_code == 400
    assert "logo_id" in response.json()["fields"]

    response = client.patch("/api/v1/company/", {"logo_id": None}, format="json")
    assert response.json()["logo"] is None


# --- Sedes --------------------------------------------------------------------------------------


def test_a_new_location_can_become_the_default(tenant):
    client = client_for(tenant)
    old_default = default_location(tenant)

    response = client.post(
        "/api/v1/locations/", {"name": "Norte", "is_default": True}, format="json"
    )

    assert response.status_code == 201
    assert str(default_location(tenant).pk) == response.json()["id"]
    listed = client.get("/api/v1/locations/").json()
    assert [(item["name"], item["is_default"]) for item in listed][0] == ("Norte", True)
    assert {item["id"]: item["is_default"] for item in listed}[str(old_default.pk)] is False


def test_the_plan_limits_how_many_locations_a_business_has(tenant):
    client = client_for(tenant)
    assert client.post("/api/v1/locations/", {"name": "Norte"}, format="json").status_code == 201

    response = client.post("/api/v1/locations/", {"name": "Sur"}, format="json")

    assert response.status_code == 409
    assert response.json()["code"] == "plan_limit_reached"


def test_the_business_can_never_be_left_without_a_default_location(tenant):
    client = client_for(tenant)
    url = f"/api/v1/locations/{default_location(tenant).pk}/"

    response = client.patch(url, {"is_default": False}, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "default_location_required"

    response = client.delete(url)
    assert response.status_code == 409
    assert response.json()["code"] == "default_location_required"


def test_choosing_another_default_moves_the_flag(tenant):
    client = client_for(tenant)
    other = client.post("/api/v1/locations/", {"name": "Norte"}, format="json").json()

    response = client.patch(
        f"/api/v1/locations/{other['id']}/", {"is_default": True}, format="json"
    )

    assert response.json()["is_default"] is True
    with tenant_context(tenant):
        assert Location.objects.filter(is_default=True).count() == 1


def test_a_location_in_use_cannot_be_deleted(tenant):
    client = client_for(tenant)
    other = client.post("/api/v1/locations/", {"name": "Norte"}, format="json").json()
    with tenant_context(tenant):
        location = Location.objects.get(pk=other["id"])
        ProfessionalFactory(location=location)

    response = client.delete(f"/api/v1/locations/{other['id']}/")

    assert response.status_code == 409
    assert response.json()["code"] == "location_in_use"


def test_an_unused_location_is_soft_deleted(tenant):
    client = client_for(tenant)
    other = client.post("/api/v1/locations/", {"name": "Norte"}, format="json").json()
    with tenant_context(tenant):
        ResourceFactory(location=default_location(tenant))  # en otra sede: no estorba

    assert client.delete(f"/api/v1/locations/{other['id']}/").status_code == 204
    assert client.get(f"/api/v1/locations/{other['id']}/").status_code == 404
    with tenant_context(tenant):
        assert Location.all_tenants.filter(pk=other["id"], deleted_at__isnull=False).exists()


def test_locations_of_another_business_are_not_found(tenant):
    other_tenant = TenantFactory()
    company.create_company(other_tenant)
    foreign = default_location(other_tenant)
    client = client_for(tenant)

    url = f"/api/v1/locations/{foreign.pk}/"
    assert client.get(url).status_code == 404
    assert client.patch(url, {"name": "Mía"}, format="json").status_code == 404
    assert client.delete(url).status_code == 404
    assert [item["id"] for item in client.get("/api/v1/locations/").json()] == [
        str(default_location(tenant).pk)
    ]
