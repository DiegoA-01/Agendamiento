import factory

from apps.notifications.models import NotificationLog
from tests.booking.factories import AppointmentFactory
from tests.catalog.factories import SAME_TENANT
from tests.tenancy.factories import TenantOwnedFactory


class NotificationLogFactory(TenantOwnedFactory):
    class Meta:
        model = NotificationLog

    appointment = factory.SubFactory(AppointmentFactory, tenant=SAME_TENANT)
    kind = NotificationLog.Kind.CONFIRMATION
    channel = NotificationLog.Channel.EMAIL
    to = "cliente@example.com"
    dedupe_key = factory.Sequence(lambda n: f"prueba:{n}")
