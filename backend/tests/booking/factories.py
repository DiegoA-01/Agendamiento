import datetime as dt
from decimal import Decimal

import factory
from django.utils import timezone

from apps.booking.models import Appointment, AppointmentItem, Customer
from tests.catalog.factories import SAME_TENANT, ProfessionalFactory, ServiceFactory
from tests.tenancy.factories import TenantOwnedFactory


class CustomerFactory(TenantOwnedFactory):
    class Meta:
        model = Customer

    full_name = "Cliente de Prueba"
    phone = factory.Sequence(lambda n: f"+57300{n:07d}")
    data_consent_at = factory.LazyFunction(timezone.now)


class AppointmentFactory(TenantOwnedFactory):
    class Meta:
        model = Appointment

    customer = factory.SubFactory(CustomerFactory, tenant=SAME_TENANT)
    professional = factory.SubFactory(ProfessionalFactory, tenant=SAME_TENANT)
    location = factory.SelfAttribute("professional.location")
    start_at = factory.LazyFunction(
        lambda: (timezone.now() + dt.timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
    )
    end_at = factory.LazyAttribute(lambda o: o.start_at + dt.timedelta(minutes=30))
    source = Appointment.Source.DASHBOARD
    price_total = Decimal("30000.00")


class AppointmentItemFactory(TenantOwnedFactory):
    class Meta:
        model = AppointmentItem

    appointment = factory.SubFactory(AppointmentFactory, tenant=SAME_TENANT)
    service = factory.SubFactory(ServiceFactory, tenant=SAME_TENANT)
    professional = factory.SelfAttribute("appointment.professional")
    price_charged = Decimal("30000.00")
    duration_min = 30
    commission_pct_snapshot = Decimal("40.00")
