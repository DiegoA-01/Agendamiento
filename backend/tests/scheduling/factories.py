import datetime as dt

import factory
from django.utils import timezone

from apps.scheduling.models import TimeBlock, WorkingHours
from tests.catalog.factories import SAME_TENANT, ProfessionalFactory
from tests.tenancy.factories import TenantOwnedFactory


class WorkingHoursFactory(TenantOwnedFactory):
    class Meta:
        model = WorkingHours

    professional = factory.SubFactory(ProfessionalFactory, tenant=SAME_TENANT)
    weekday = 0
    start_time = dt.time(9, 0)
    end_time = dt.time(19, 0)


class TimeBlockFactory(TenantOwnedFactory):
    """Bloqueo de un profesional. Para un puesto: `professional=None, resource=...`."""

    class Meta:
        model = TimeBlock

    professional = factory.SubFactory(ProfessionalFactory, tenant=SAME_TENANT)
    start_at = factory.LazyFunction(lambda: timezone.now() + dt.timedelta(days=1))
    end_at = factory.LazyAttribute(lambda o: o.start_at + dt.timedelta(hours=1))
    reason = "Almuerzo"
