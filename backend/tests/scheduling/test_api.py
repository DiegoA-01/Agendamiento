import datetime as dt

import pytest
from rest_framework.test import APIClient

from apps.booking.models import Appointment
from apps.scheduling.models import TimeBlock, WorkingHours
from apps.tenancy.context import tenant_context
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import ADMIN_HOST, host, login
from tests.booking.factories import AppointmentFactory
from tests.catalog.factories import ProfessionalFactory, ResourceFactory
from tests.scheduling.factories import TimeBlockFactory, WorkingHoursFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db

STAFF_ROLES = ["owner", "admin", "receptionist"]
# El negocio usa America/Bogota (UTC-5) por defecto.
BOGOTA = dt.timezone(dt.timedelta(hours=-5))


@pytest.fixture
def tenant():
    return TenantFactory()


def make(tenant, factory, **kwargs):
    with tenant_context(tenant):
        return factory(**kwargs)


def client_for(tenant, role="owner"):
    user = UserFactory(tenant=tenant, role=role)
    client = APIClient()
    login(client, user, host(tenant.slug))
    client.defaults["HTTP_HOST"] = host(tenant.slug)
    return client, user


def professional_client(tenant):
    """Cliente de un profesional con su ficha enlazada. Devuelve (cliente, su ficha)."""
    client, user = client_for(tenant, "professional")
    return client, make(tenant, ProfessionalFactory, user=user)


def hours_url(professional):
    return f"/api/v1/professionals/{professional.pk}/working-hours/"


WEEK = [
    {"weekday": 0, "start_time": "09:00", "end_time": "12:00"},
    {"weekday": 0, "start_time": "14:00", "end_time": "19:00"},
    {"weekday": 5, "start_time": "08:00", "end_time": "13:00"},
]


# --- Horarios de trabajo ---------------------------------------------------------------------


@pytest.mark.parametrize("role", STAFF_ROLES)
def test_staff_can_replace_and_read_the_week_of_any_professional(tenant, role):
    professional = make(tenant, ProfessionalFactory)
    client, _ = client_for(tenant, role)

    response = client.put(hours_url(professional), WEEK, format="json")

    assert response.status_code == 200, response.json()
    assert response.json() == [
        {**i, "start_time": i["start_time"] + ":00", "end_time": i["end_time"] + ":00"}
        for i in WEEK
    ]
    assert client.get(hours_url(professional)).json() == response.json()


def test_replacing_the_week_drops_the_previous_intervals(tenant):
    professional = make(tenant, ProfessionalFactory)
    make(tenant, WorkingHoursFactory, professional=professional, weekday=3)
    client, _ = client_for(tenant)

    client.put(hours_url(professional), WEEK[:1], format="json")

    with tenant_context(tenant):
        assert list(WorkingHours.objects.values_list("weekday", flat=True)) == [0]
        # Borrado lógico: la fila vieja sigue en la tabla con fecha de borrado.
        assert WorkingHours.all_tenants.filter(deleted_at__isnull=False).count() == 1


def test_an_empty_week_leaves_the_professional_without_hours(tenant):
    professional = make(tenant, ProfessionalFactory)
    make(tenant, WorkingHoursFactory, professional=professional)
    client, _ = client_for(tenant)

    assert client.put(hours_url(professional), [], format="json").json() == []


@pytest.mark.parametrize(
    "week, code, field",
    [
        ([{"weekday": 7, "start_time": "09:00", "end_time": "10:00"}], "validation_error", None),
        ([{"weekday": 1, "start_time": "10:00", "end_time": "09:00"}], "validation_error", None),
        (
            [
                {"weekday": 1, "start_time": "09:00", "end_time": "13:00"},
                {"weekday": 1, "start_time": "12:00", "end_time": "18:00"},
            ],
            "overlapping_hours",
            "weekday",
        ),
        ({"weekday": 1}, "validation_error", None),
    ],
)
def test_invalid_weeks_are_rejected_and_nothing_changes(tenant, week, code, field):
    professional = make(tenant, ProfessionalFactory)
    make(tenant, WorkingHoursFactory, professional=professional)
    client, _ = client_for(tenant)

    response = client.put(hours_url(professional), week, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == code
    if field:
        assert field in response.json()["fields"]
    with tenant_context(tenant):
        assert WorkingHours.objects.count() == 1


def test_intervals_that_only_touch_are_a_valid_week(tenant):
    professional = make(tenant, ProfessionalFactory)
    client, _ = client_for(tenant)
    week = [
        {"weekday": 2, "start_time": "09:00", "end_time": "12:00"},
        {"weekday": 2, "start_time": "12:00", "end_time": "18:00"},
    ]
    assert client.put(hours_url(professional), week, format="json").status_code == 200


def test_a_professional_manages_only_their_own_hours(tenant):
    client, own = professional_client(tenant)
    other = make(tenant, ProfessionalFactory)

    assert client.put(hours_url(own), WEEK, format="json").status_code == 200
    # Lo ajeno no existe para él: 404, no 403.
    assert client.get(hours_url(other)).status_code == 404
    assert client.put(hours_url(other), WEEK, format="json").status_code == 404


def test_a_professional_account_without_a_profile_sees_no_hours(tenant):
    client, _ = client_for(tenant, "professional")
    assert client.get(hours_url(make(tenant, ProfessionalFactory))).status_code == 404


def test_hours_of_another_business_are_not_found(tenant):
    other_business_professional = make(TenantFactory(), ProfessionalFactory)
    client, _ = client_for(tenant)

    assert client.get(hours_url(other_business_professional)).status_code == 404
    assert (
        client.put(hours_url(other_business_professional), WEEK, format="json").status_code == 404
    )


def test_anonymous_and_platform_host_cannot_read_hours(tenant):
    professional = make(tenant, ProfessionalFactory)
    assert APIClient().get(hours_url(professional), HTTP_HOST=host(tenant.slug)).status_code == 401
    assert APIClient().get(hours_url(professional), HTTP_HOST=ADMIN_HOST).status_code in (401, 403)


# --- Bloqueos ----------------------------------------------------------------------------------


def block_payload(owner_field, owner, start, hours=1, **extra):
    return {
        owner_field: str(owner.pk),
        "start_at": start.isoformat(),
        "end_at": (start + dt.timedelta(hours=hours)).isoformat(),
        "reason": "Capacitación",
        **extra,
    }


def tomorrow_at(hour):
    day = dt.date.today() + dt.timedelta(days=1)
    return dt.datetime.combine(day, dt.time(hour), tzinfo=BOGOTA)


@pytest.mark.parametrize("role", STAFF_ROLES)
def test_staff_can_block_a_professional_and_a_resource(tenant, role):
    professional = make(tenant, ProfessionalFactory)
    resource = make(tenant, ResourceFactory)
    client, _ = client_for(tenant, role)

    for field, owner in (("professional_id", professional), ("resource_id", resource)):
        response = client.post(
            "/api/v1/time-blocks/", block_payload(field, owner, tomorrow_at(9)), format="json"
        )
        assert response.status_code == 201, response.json()
        assert response.json()[field] == str(owner.pk)
        assert response.json()["reason"] == "Capacitación"


def test_dates_are_returned_in_the_business_timezone(tenant):
    professional = make(tenant, ProfessionalFactory)
    client, _ = client_for(tenant)

    # Sin zona: se interpreta en hora del negocio.
    response = client.post(
        "/api/v1/time-blocks/",
        {
            "professional_id": str(professional.pk),
            "start_at": "2030-01-10T09:00",
            "end_at": "2030-01-10T10:00",
        },
        format="json",
    )

    assert response.json()["start_at"] == "2030-01-10T09:00:00-05:00"
    with tenant_context(tenant):
        stored = TimeBlock.objects.get()
        assert stored.start_at == dt.datetime(2030, 1, 10, 14, 0, tzinfo=dt.UTC)


def test_a_block_that_overlaps_appointments_returns_409_with_them(tenant):
    professional = make(tenant, ProfessionalFactory)
    clash = make(
        tenant,
        AppointmentFactory,
        professional=professional,
        start_at=tomorrow_at(10),
        end_at=tomorrow_at(10) + dt.timedelta(minutes=30),
    )
    make(  # cancelada: ya liberó el hueco, no cuenta
        tenant,
        AppointmentFactory,
        professional=professional,
        status=Appointment.Status.CANCELLED,
        start_at=tomorrow_at(11),
        end_at=tomorrow_at(11) + dt.timedelta(minutes=30),
    )
    client, _ = client_for(tenant)

    response = client.post(
        "/api/v1/time-blocks/",
        block_payload("professional_id", professional, tomorrow_at(9), hours=3),
        format="json",
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "time_block_conflict"
    assert [a["id"] for a in body["fields"]["appointments"]] == [str(clash.pk)]
    assert body["fields"]["appointments"][0]["start_at"].endswith("-05:00")
    with tenant_context(tenant):
        assert not TimeBlock.objects.exists()


def test_a_block_that_ends_when_an_appointment_starts_is_allowed(tenant):
    professional = make(tenant, ProfessionalFactory)
    make(
        tenant,
        AppointmentFactory,
        professional=professional,
        start_at=tomorrow_at(10),
        end_at=tomorrow_at(11),
    )
    client, _ = client_for(tenant)

    response = client.post(
        "/api/v1/time-blocks/",
        block_payload("professional_id", professional, tomorrow_at(9)),
        format="json",
    )
    assert response.status_code == 201


def test_a_resource_block_checks_the_appointments_of_that_resource(tenant):
    resource = make(tenant, ResourceFactory)
    make(
        tenant,
        AppointmentFactory,
        resource=resource,
        start_at=tomorrow_at(9),
        end_at=tomorrow_at(10),
    )
    client, _ = client_for(tenant)

    response = client.post(
        "/api/v1/time-blocks/",
        block_payload("resource_id", resource, tomorrow_at(9)),
        format="json",
    )
    assert response.status_code == 409


@pytest.mark.parametrize("owners", [{}, "both"])
def test_a_block_needs_exactly_one_owner(tenant, owners):
    client, _ = client_for(tenant)
    payload = {"start_at": tomorrow_at(9).isoformat(), "end_at": tomorrow_at(10).isoformat()}
    if owners == "both":
        payload["professional_id"] = str(make(tenant, ProfessionalFactory).pk)
        payload["resource_id"] = str(make(tenant, ResourceFactory).pk)

    response = client.post("/api/v1/time-blocks/", payload, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_a_block_must_end_after_it_starts(tenant):
    professional = make(tenant, ProfessionalFactory)
    client, _ = client_for(tenant)
    response = client.post(
        "/api/v1/time-blocks/",
        block_payload("professional_id", professional, tomorrow_at(9), hours=0),
        format="json",
    )
    assert response.status_code == 400
    assert "end_at" in response.json()["fields"]


def test_cannot_block_a_professional_or_resource_of_another_business(tenant):
    other = TenantFactory()
    client, _ = client_for(tenant)
    for field, owner in (
        ("professional_id", make(other, ProfessionalFactory)),
        ("resource_id", make(other, ResourceFactory)),
    ):
        response = client.post(
            "/api/v1/time-blocks/", block_payload(field, owner, tomorrow_at(9)), format="json"
        )
        assert response.status_code == 404


def test_list_filters_by_owner_and_range(tenant):
    professional = make(tenant, ProfessionalFactory)
    resource = make(tenant, ResourceFactory)
    early = make(
        tenant,
        TimeBlockFactory,
        professional=professional,
        start_at=tomorrow_at(8),
        end_at=tomorrow_at(9),
    )
    late = make(
        tenant,
        TimeBlockFactory,
        professional=professional,
        start_at=tomorrow_at(15),
        end_at=tomorrow_at(16),
    )
    on_resource = make(
        tenant,
        TimeBlockFactory,
        professional=None,
        resource=resource,
        start_at=tomorrow_at(8),
        end_at=tomorrow_at(9),
    )
    client, _ = client_for(tenant)

    def ids(**params):
        response = client.get("/api/v1/time-blocks/", params)
        assert response.status_code == 200, response.json()
        return [b["id"] for b in response.json()["results"]]

    everything = ids()
    assert everything[-1] == str(late.pk)  # ordenados por inicio
    assert set(everything) == {str(early.pk), str(on_resource.pk), str(late.pk)}
    assert ids(professional_id=professional.pk) == [str(early.pk), str(late.pk)]
    assert ids(resource_id=resource.pk) == [str(on_resource.pk)]
    window = {"start_at": tomorrow_at(12).isoformat(), "end_at": tomorrow_at(18).isoformat()}
    assert ids(**window) == [str(late.pk)]


def test_update_moves_a_block_and_rechecks_appointments(tenant):
    professional = make(tenant, ProfessionalFactory)
    block = make(
        tenant,
        TimeBlockFactory,
        professional=professional,
        start_at=tomorrow_at(8),
        end_at=tomorrow_at(9),
    )
    make(
        tenant,
        AppointmentFactory,
        professional=professional,
        start_at=tomorrow_at(12),
        end_at=tomorrow_at(13),
    )
    client, _ = client_for(tenant)
    url = f"/api/v1/time-blocks/{block.pk}/"

    moved = client.patch(
        url, {"end_at": tomorrow_at(10).isoformat(), "reason": "Médico"}, format="json"
    )
    assert moved.status_code == 200, moved.json()
    assert moved.json()["reason"] == "Médico"

    clash = client.patch(
        url, {"end_at": tomorrow_at(12).replace(minute=30).isoformat()}, format="json"
    )
    assert clash.status_code == 409

    backwards = client.patch(url, {"end_at": tomorrow_at(7).isoformat()}, format="json")
    assert backwards.status_code == 400


def test_delete_is_logical(tenant):
    block = make(tenant, TimeBlockFactory)
    client, _ = client_for(tenant)

    assert client.delete(f"/api/v1/time-blocks/{block.pk}/").status_code == 204
    assert client.get(f"/api/v1/time-blocks/{block.pk}/").status_code == 404
    with tenant_context(tenant):
        assert TimeBlock.all_tenants.get(pk=block.pk).deleted_at is not None


def test_a_professional_sees_and_manages_only_their_own_blocks(tenant):
    client, own = professional_client(tenant)
    other = make(tenant, ProfessionalFactory)
    mine = make(tenant, TimeBlockFactory, professional=own)
    theirs = make(tenant, TimeBlockFactory, professional=other)
    resource_block = make(
        tenant, TimeBlockFactory, professional=None, resource=make(tenant, ResourceFactory)
    )

    listed = [b["id"] for b in client.get("/api/v1/time-blocks/").json()["results"]]
    assert listed == [str(mine.pk)]

    for block in (theirs, resource_block):
        url = f"/api/v1/time-blocks/{block.pk}/"
        assert client.get(url).status_code == 404
        assert client.patch(url, {"reason": "x"}, format="json").status_code == 404
        assert client.delete(url).status_code == 404

    own_new = client.post(
        "/api/v1/time-blocks/",
        block_payload("professional_id", own, tomorrow_at(9)),
        format="json",
    )
    assert own_new.status_code == 201
    other_new = client.post(
        "/api/v1/time-blocks/",
        block_payload("professional_id", other, tomorrow_at(9)),
        format="json",
    )
    assert other_new.status_code == 404
    resource_new = client.post(
        "/api/v1/time-blocks/",
        block_payload("resource_id", make(tenant, ResourceFactory), tomorrow_at(9)),
        format="json",
    )
    assert resource_new.status_code == 403


def test_blocks_of_another_business_are_invisible(tenant):
    foreign = make(TenantFactory(), TimeBlockFactory)
    client, _ = client_for(tenant)

    assert client.get("/api/v1/time-blocks/").json()["results"] == []
    assert client.get(f"/api/v1/time-blocks/{foreign.pk}/").status_code == 404
    assert client.delete(f"/api/v1/time-blocks/{foreign.pk}/").status_code == 404
