from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.catalog import services as catalog
from apps.catalog.models import Professional, ProfessionalService
from apps.company import services as company
from apps.tenancy.context import tenant_context
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import host
from tests.catalog.factories import (
    ProfessionalFactory,
    ProfessionalServiceFactory,
    ServiceFactory,
    SpecialtyFactory,
)
from tests.media.factories import MediaFileFactory
from tests.tenancy.factories import PlanFactory, TenantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant():
    tenant = TenantFactory(plan=PlanFactory(max_professionals=3))
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


# --- Permisos -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role, can_write", [("owner", True), ("admin", True), ("receptionist", False),
                        ("professional", False)]
)  # fmt: skip
def test_team_permissions_by_role(tenant, role, can_write):
    client = client_for(tenant, role)
    assert client.get("/api/v1/professionals/").status_code == 200
    response = client.post("/api/v1/professionals/", {"display_name": "Ana"}, format="json")
    assert response.status_code == (201 if can_write else 403)
    assert client.post("/api/v1/specialties/", {"name": "Fade"}, format="json").status_code == (
        201 if can_write else 403
    )


def test_a_professional_only_sees_their_own_profile(tenant):
    user = UserFactory(tenant=tenant, role="professional")
    mine = in_tenant(tenant, ProfessionalFactory, user=user, display_name="Yo")
    other = in_tenant(tenant, ProfessionalFactory, display_name="Otro")
    client = client_for(tenant, user=user)

    assert [p["display_name"] for p in client.get("/api/v1/professionals/").json()] == ["Yo"]
    assert client.get(f"/api/v1/professionals/{mine.pk}/").status_code == 200
    assert client.get(f"/api/v1/professionals/{other.pk}/").status_code == 404
    assert client.get(f"/api/v1/professionals/{other.pk}/services/").status_code == 404


# --- Fichas -------------------------------------------------------------------------------------


def test_owner_creates_a_full_profile(tenant):
    account = UserFactory(tenant=tenant, role="professional")
    with tenant_context(tenant):
        photo, fade, beard = MediaFileFactory(), SpecialtyFactory(name="Fade"), SpecialtyFactory()
    client = client_for(tenant)

    response = client.post(
        "/api/v1/professionals/",
        {
            "display_name": "Ana",
            "bio": "10 años de experiencia",
            "user_id": str(account.pk),
            "photo_id": str(photo.pk),
            "specialty_ids": [str(fade.pk), str(beard.pk)],
            "default_commission_pct": "45.5",
            "accepts_online_booking": False,
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["user_id"] == str(account.pk)
    assert body["location_id"] == str(company.get_default_location(tenant).pk)
    assert body["photo"]["id"] == str(photo.pk)
    assert set(body["specialty_ids"]) == {str(fade.pk), str(beard.pk)}
    assert body["default_commission_pct"] == "45.50"
    assert body["accepts_online_booking"] is False

    response = client.patch(
        f"/api/v1/professionals/{body['id']}/", {"specialty_ids": [str(fade.pk)]}, format="json"
    )
    assert response.json()["specialty_ids"] == [str(fade.pk)]


@pytest.mark.parametrize("value", ["-1", "100.01", "12.345"])
def test_the_commission_is_a_percentage(tenant, value):
    response = client_for(tenant).post(
        "/api/v1/professionals/",
        {"display_name": "Ana", "default_commission_pct": value},
        format="json",
    )
    assert response.status_code == 400
    assert "default_commission_pct" in response.json()["fields"]


def test_an_account_can_have_only_one_profile(tenant):
    account = UserFactory(tenant=tenant, role="professional")
    client = client_for(tenant)
    payload = {"display_name": "Ana", "user_id": str(account.pk)}
    assert client.post("/api/v1/professionals/", payload, format="json").status_code == 201

    response = client.post("/api/v1/professionals/", payload, format="json")
    assert response.status_code == 400
    assert "user_id" in response.json()["fields"]


def test_links_to_another_business_are_rejected(tenant):
    other = TenantFactory()
    foreign_account = UserFactory(tenant=other, role="professional")
    with tenant_context(other):
        foreign_photo, foreign_specialty = MediaFileFactory(), SpecialtyFactory()
    client = client_for(tenant)

    for field, value in [
        ("user_id", str(foreign_account.pk)),
        ("photo_id", str(foreign_photo.pk)),
        ("specialty_ids", [str(foreign_specialty.pk)]),
    ]:
        response = client.post(
            "/api/v1/professionals/", {"display_name": "Ana", field: value}, format="json"
        )
        assert response.status_code == 400, field
        assert field in response.json()["fields"]


def test_the_plan_limits_the_team_size_and_deleting_frees_a_seat(tenant):
    client = client_for(tenant)
    created = [
        client.post("/api/v1/professionals/", {"display_name": f"P{n}"}, format="json")
        for n in range(3)
    ]
    assert [r.status_code for r in created] == [201, 201, 201]

    response = client.post("/api/v1/professionals/", {"display_name": "P4"}, format="json")
    assert response.status_code == 409
    assert response.json()["code"] == "plan_limit_reached"

    assert client.delete(f"/api/v1/professionals/{created[0].json()['id']}/").status_code == 204
    assert (
        client.post("/api/v1/professionals/", {"display_name": "P4"}, format="json").status_code
        == 201
    )


def test_deleting_a_professional_removes_their_offer(tenant):
    link = in_tenant(tenant, ProfessionalServiceFactory)
    client = client_for(tenant)

    assert client.delete(f"/api/v1/professionals/{link.professional_id}/").status_code == 204

    with tenant_context(tenant):
        assert not Professional.objects.filter(pk=link.professional_id).exists()
        assert not ProfessionalService.objects.filter(pk=link.pk).exists()
        assert catalog.professionals_for_services([link.service]) == []


# --- Servicios del profesional ------------------------------------------------------------------


def test_assigning_services_with_overrides_feeds_the_quote(tenant):
    with tenant_context(tenant):
        professional = ProfessionalFactory(default_commission_pct=Decimal("40"))
        cut = ServiceFactory(name="Corte", price=Decimal("30000"), duration_min=30)
        beard = ServiceFactory(name="Barba", price=Decimal("15000"), duration_min=20)
    client = client_for(tenant)
    url = f"/api/v1/professionals/{professional.pk}/services/"

    response = client.put(
        url,
        {
            "services": [
                {"service_id": str(cut.pk), "price_override": "35000", "duration_override_min": 40},
                {"service_id": str(beard.pk), "commission_pct_override": "50"},
            ]
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    offers = {o["service_name"]: o for o in response.json()["services"]}
    assert offers["Corte"]["price_override"] == "35000.00"
    assert offers["Barba"]["price_override"] is None
    with tenant_context(tenant):
        result = catalog.quote(professional, [cut, beard])
    assert [i.price for i in result.items] == [Decimal("35000.00"), Decimal("15000.00")]
    assert [i.commission_pct for i in result.items] == [Decimal("40.00"), Decimal("50.00")]
    assert result.total_duration_min == 60


def test_replacing_the_list_drops_missing_services_and_keeps_existing_ids(tenant):
    with tenant_context(tenant):
        professional = ProfessionalFactory()
        kept, dropped = ServiceFactory(), ServiceFactory()
        kept_link = ProfessionalServiceFactory(professional=professional, service=kept)
        ProfessionalServiceFactory(professional=professional, service=dropped)
    client = client_for(tenant)
    url = f"/api/v1/professionals/{professional.pk}/services/"

    response = client.put(url, {"services": [{"service_id": str(kept.pk)}]}, format="json")

    assert [o["service_id"] for o in response.json()["services"]] == [str(kept.pk)]
    with tenant_context(tenant):
        assert ProfessionalService.objects.get(service=kept).pk == kept_link.pk
        assert catalog.quote(professional, [dropped]) is None
    assert client.put(url, {"services": []}, format="json").json() == {"services": []}


@pytest.mark.parametrize("problem", ["other_tenant", "repeated", "bad_override"])
def test_invalid_assignments_are_rejected(tenant, problem):
    professional = in_tenant(tenant, ProfessionalFactory)
    service = in_tenant(tenant, ServiceFactory)
    offers = [{"service_id": str(service.pk)}]
    if problem == "other_tenant":
        offers = [{"service_id": str(in_tenant(TenantFactory(), ServiceFactory).pk)}]
    elif problem == "repeated":
        offers = offers * 2
    elif problem == "bad_override":
        offers = [{"service_id": str(service.pk), "commission_pct_override": "150"}]

    response = client_for(tenant).put(
        f"/api/v1/professionals/{professional.pk}/services/", {"services": offers}, format="json"
    )
    assert response.status_code == 400
    assert "services" in response.json()["fields"]


def test_only_editors_can_assign_services(tenant):
    professional = in_tenant(tenant, ProfessionalFactory)
    response = client_for(tenant, "receptionist").put(
        f"/api/v1/professionals/{professional.pk}/services/", {"services": []}, format="json"
    )
    assert response.status_code == 403


# --- Especialidades y aislamiento ---------------------------------------------------------------


def test_deleting_a_specialty_unlinks_it_from_profiles(tenant):
    client = client_for(tenant)
    specialty = client.post("/api/v1/specialties/", {"name": "Fade"}, format="json").json()
    professional = client.post(
        "/api/v1/professionals/",
        {"display_name": "Ana", "specialty_ids": [specialty["id"]]},
        format="json",
    ).json()

    assert client.delete(f"/api/v1/specialties/{specialty['id']}/").status_code == 204
    assert client.get(f"/api/v1/professionals/{professional['id']}/").json()["specialty_ids"] == []
    assert client.get("/api/v1/specialties/").json() == []


def test_professionals_of_another_business_are_not_found(tenant):
    foreign = in_tenant(TenantFactory(), ProfessionalFactory)
    client = client_for(tenant)
    url = f"/api/v1/professionals/{foreign.pk}/"

    assert client.get(url).status_code == 404
    assert client.patch(url, {"display_name": "Mío"}, format="json").status_code == 404
    assert client.delete(url).status_code == 404
    assert client.put(f"{url}services/", {"services": []}, format="json").status_code == 404
    assert client.get("/api/v1/professionals/").json() == []
