import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from apps.booking.models import Appointment
from apps.scheduling import availability
from apps.scheduling import services as scheduling
from apps.tenancy.context import tenant_context
from config.api import ApiError
from tests.accounts.factories import UserFactory
from tests.booking.factories import AppointmentFactory
from tests.catalog.factories import (
    ProfessionalFactory,
    ProfessionalServiceFactory,
    ResourceFactory,
    ServiceFactory,
)
from tests.scheduling.factories import TimeBlockFactory, WorkingHoursFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db

BOGOTA = ZoneInfo("America/Bogota")


def next_monday(weeks_ahead: int = 1) -> dt.date:
    today = dt.date.today()
    return (
        today
        + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)
        + dt.timedelta(weeks=weeks_ahead - 1)
    )


DAY = next_monday()


def at(hour: int, minute: int = 0, day: dt.date = DAY) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hour, minute), tzinfo=BOGOTA)


def hhmm(slots) -> list[str]:
    return [slot.start.strftime("%H:%M") for slot in slots]


@pytest.fixture
def tenant():
    tenant = TenantFactory()
    with tenant_context(tenant):
        yield tenant


@pytest.fixture
def service(tenant):
    return ServiceFactory(duration_min=30, buffer_min=0)


def make_professional(service, name="Ana", **link):
    professional = ProfessionalFactory(display_name=name)
    ProfessionalServiceFactory(professional=professional, service=service, **link)
    WorkingHoursFactory(
        professional=professional, weekday=0, start_time=dt.time(9), end_time=dt.time(12)
    )
    WorkingHoursFactory(
        professional=professional, weekday=0, start_time=dt.time(14), end_time=dt.time(18)
    )
    return professional


def slots(tenant, service, professional=None, day=DAY, public=False):
    return availability.get_available_slots(
        tenant, [service.pk], day, professional.pk if professional else None, public=public
    )


# --- Algoritmo (spec §8) ------------------------------------------------------------------------


def test_slots_follow_working_hours_every_step_where_the_service_fits(tenant, service):
    professional = make_professional(service)

    result = slots(tenant, service, professional)

    # 30 min cada 15: la mañana termina a las 12:00, el último inicio es 11:30.
    assert hhmm(result)[:3] == ["09:00", "09:15", "09:30"]
    assert "11:30" in hhmm(result) and "11:45" not in hhmm(result)
    assert "12:00" not in hhmm(result) and "14:00" in hhmm(result)
    assert hhmm(result)[-1] == "17:30"
    assert len(result) == 11 + 15
    assert result[0].start.utcoffset() == dt.timedelta(hours=-5)
    assert result[0].end - result[0].start == dt.timedelta(minutes=30)


def test_slots_are_grouped_into_morning_afternoon_and_evening(tenant, service):
    professional = make_professional(service)
    WorkingHoursFactory(
        professional=professional, weekday=0, start_time=dt.time(18), end_time=dt.time(19)
    )
    periods = {slot.start.strftime("%H:%M"): slot.period for slot in slots(tenant, service)}
    assert periods["11:30"] == "morning"
    assert periods["14:00"] == "afternoon"
    assert periods["17:30"] == "afternoon"
    assert periods["18:00"] == "evening"


def test_time_blocks_and_active_appointments_take_time_away(tenant, service):
    professional = make_professional(service)
    TimeBlockFactory(professional=professional, start_at=at(10), end_at=at(11))
    AppointmentFactory(professional=professional, start_at=at(15), end_at=at(15, 30))
    AppointmentFactory(
        professional=professional,
        start_at=at(16),
        end_at=at(16, 30),
        status=Appointment.Status.CANCELLED,
    )

    starts = hhmm(slots(tenant, service, professional))

    assert "09:30" in starts and "09:45" not in starts  # 9:45 terminaría 10:15
    assert "10:45" not in starts and "11:00" in starts
    assert {"14:45", "15:00", "15:15"}.isdisjoint(starts)
    assert "16:00" in starts  # la cancelada ya liberó el hueco


def test_duration_uses_the_professional_override_plus_the_last_buffer(tenant):
    first = ServiceFactory(duration_min=30, buffer_min=5)
    last = ServiceFactory(duration_min=15, buffer_min=10)
    professional = make_professional(first, duration_override_min=45)
    ProfessionalServiceFactory(professional=professional, service=last)

    result = availability.get_available_slots(
        tenant, [first.pk, last.pk], DAY, professional.pk, public=False
    )

    # 45 (override) + 15 + 10 (buffer del último) = 70 minutos.
    assert result[0].end - result[0].start == dt.timedelta(minutes=70)
    assert "10:45" in hhmm(result) and "11:00" not in hhmm(result)


def test_any_professional_joins_the_slots_of_everyone_who_offers_all_services(tenant, service):
    ana = make_professional(service, "Ana")
    beto = ProfessionalFactory(display_name="Beto")
    ProfessionalServiceFactory(professional=beto, service=service)
    WorkingHoursFactory(professional=beto, weekday=0, start_time=dt.time(12), end_time=dt.time(13))
    ProfessionalFactory(display_name="Carla")  # no ofrece el servicio

    result = slots(tenant, service)

    assert "12:00" in hhmm(result)  # solo Beto trabaja a esa hora
    by_start = {slot.start.strftime("%H:%M"): slot.professional_ids for slot in result}
    assert by_start["12:00"] == (beto.pk,)
    assert by_start["09:00"] == (ana.pk,)


def test_a_service_that_needs_a_resource_needs_a_free_one_at_the_same_location(tenant):
    service = ServiceFactory(duration_min=30, requires_resource=True)
    professional = make_professional(service)
    assert slots(tenant, service, professional) == []  # la sede no tiene puestos

    chair = ResourceFactory(location=professional.location)
    AppointmentFactory(
        professional=ProfessionalFactory(location=professional.location),
        resource=chair,
        start_at=at(9),
        end_at=at(10),
    )
    TimeBlockFactory(professional=None, resource=chair, start_at=at(14), end_at=at(15))

    starts = hhmm(slots(tenant, service, professional))
    assert "09:30" not in starts and "10:00" in starts
    assert "14:30" not in starts and "15:00" in starts


def test_the_public_window_applies_minimum_notice_and_days_ahead(tenant, service):
    professional = make_professional(service)
    window = availability.Window(earliest=at(10), last_day=DAY)
    starts = hhmm(availability.slots_for_day(tenant, [service], DAY, [professional], window=window))
    assert starts[0] == "10:00"

    far = next_monday(weeks_ahead=12)  # más de 60 días
    assert slots(tenant, service, professional, day=far, public=True) == []
    assert slots(tenant, service, professional, day=far, public=False) != []


def test_public_booking_skips_professionals_without_online_booking(tenant, service):
    professional = make_professional(service)
    professional.accepts_online_booking = False
    professional.save()
    assert slots(tenant, service, public=True) == []
    assert slots(tenant, service, public=False) != []


def test_past_days_have_no_slots(tenant, service):
    make_professional(service)
    last_monday = DAY - dt.timedelta(weeks=2)
    assert slots(tenant, service, day=last_monday) == []


def test_available_days_lists_only_days_with_slots(tenant, service):
    make_professional(service)  # solo trabaja los lunes
    far = next_monday(weeks_ahead=6)

    days = availability.get_available_days(tenant, [service.pk], far.year, far.month, public=False)

    assert days and all(day.weekday() == 0 for day in days)
    assert far in days


def test_unknown_services_and_professionals_that_do_not_offer_them_are_rejected(tenant, service):
    other = ProfessionalFactory()
    with pytest.raises(ApiError) as error:
        availability.get_available_slots(tenant, [], DAY, public=False)
    assert error.value.code == "invalid_services"
    with pytest.raises(ApiError) as error:
        slots(tenant, service, other)
    assert error.value.code == "professional_unavailable"


# --- Caché --------------------------------------------------------------------------------------


def test_free_time_is_cached_and_invalidated_when_the_agenda_changes(tenant, service):
    professional = make_professional(service)
    assert "09:00" in hhmm(slots(tenant, service, professional))

    # Un cambio que no pasa por los servicios no se ve hasta invalidar: prueba que hay caché.
    TimeBlockFactory(professional=professional, start_at=at(9), end_at=at(9, 30))
    assert "09:00" in hhmm(slots(tenant, service, professional))
    availability.invalidate(tenant.pk)
    assert "09:00" not in hhmm(slots(tenant, service, professional))

    # Los servicios de horarios y bloqueos invalidan solos.
    user = UserFactory(tenant=tenant, role="owner")
    scheduling.create_time_block(
        user, start_at=at(11), end_at=at(12), professional_id=professional.pk
    )
    assert "11:00" not in hhmm(slots(tenant, service, professional))
