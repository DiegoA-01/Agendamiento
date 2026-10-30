import datetime as dt

import pytest
from django.db import IntegrityError, transaction

from apps.booking.models import Appointment
from apps.tenancy.context import tenant_context
from tests.booking.factories import AppointmentFactory, CustomerFactory
from tests.catalog.factories import ResourceFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant():
    tenant = TenantFactory()
    with tenant_context(tenant):
        yield tenant


def test_two_active_appointments_of_the_same_professional_cannot_overlap(tenant):
    first = AppointmentFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        AppointmentFactory(
            professional=first.professional,
            start_at=first.start_at + dt.timedelta(minutes=15),
            end_at=first.end_at + dt.timedelta(minutes=15),
        )


def test_back_to_back_appointments_do_not_overlap(tenant):
    first = AppointmentFactory()
    AppointmentFactory(
        professional=first.professional,
        start_at=first.end_at,
        end_at=first.end_at + dt.timedelta(minutes=30),
    )


@pytest.mark.parametrize(
    "status",
    [Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW, Appointment.Status.RESCHEDULED],
)
def test_released_statuses_free_the_slot(tenant, status):
    first = AppointmentFactory(status=status)
    AppointmentFactory(professional=first.professional, start_at=first.start_at)


def test_different_professionals_can_share_the_same_time(tenant):
    first = AppointmentFactory()
    AppointmentFactory(start_at=first.start_at)


def test_the_same_resource_cannot_be_booked_twice_at_the_same_time(tenant):
    resource = ResourceFactory()
    first = AppointmentFactory(resource=resource)
    with pytest.raises(IntegrityError), transaction.atomic():
        AppointmentFactory(resource=resource, start_at=first.start_at)


def test_customer_phone_is_unique_per_tenant_only(tenant):
    CustomerFactory(phone="+573001112233")
    with pytest.raises(IntegrityError), transaction.atomic():
        CustomerFactory(phone="+573001112233")
    with tenant_context(TenantFactory()):
        CustomerFactory(phone="+573001112233")
