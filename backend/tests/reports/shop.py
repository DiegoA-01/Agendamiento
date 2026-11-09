"""Negocio con citas de marzo y abril de 2026 y los valores esperados calculados a mano.

Zona horaria del negocio: America/Bogota (UTC-5).

| Cita | Profesional (pct) | Fecha local      | Estado      | Servicios                      |
| ---- | ----------------- | ---------------- | ----------- | ------------------------------ |
| a1   | Ana (40 %)        | lun 2 mar 10:00  | completed   | Corte 30.000 + Barba 15.000    |
| a2   | Ana (40 %)        | lun 2 mar 15:00  | completed   | Corte 30.000                   |
| a3   | Luis (35,5 %)     | lun 9 mar 09:00  | completed   | Corte 33.333                   |
| a4   | Luis (35,5 %)     | mar 10 mar 11:00 | cancelled   | Corte 30.000                   |
| a5   | Ana (40 %)        | mar 31 mar 23:30 | completed   | Barba 15.000 (1 abr en UTC)    |
| a6   | Luis (35,5 %)     | mié 1 abr 10:00  | no_show     | Corte 30.000                   |
| a7   | Ana (40 %)        | mar 3 mar 10:00  | rescheduled | Corte 30.000                   |

Comisiones: 30.000 × 40 % = 12.000; 15.000 × 40 % = 6.000;
33.333 × 35,5 % = 11.833,215 → 11.833,22 (mitad hacia arriba), negocio 21.499,78.
"""

import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

from rest_framework.test import APIClient

from apps.commissions import services as commissions
from apps.tenancy import services as tenancy
from apps.tenancy.context import tenant_context
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import host, login
from tests.booking.factories import AppointmentFactory, AppointmentItemFactory
from tests.catalog.factories import ProfessionalFactory, ServiceFactory
from tests.tenancy.factories import TenantFactory

BOGOTA = ZoneInfo("America/Bogota")


def local(month: int, day: int, hour: int, minute: int = 0) -> dt.datetime:
    return dt.datetime(2026, month, day, hour, minute, tzinfo=BOGOTA)


class ReportShop:
    def __init__(self):
        self.tenant = TenantFactory(timezone="America/Bogota")
        tenancy.set_modules(self.tenant, {"commissions": True, "reports": True})
        with tenant_context(self.tenant):
            self.cut = ServiceFactory(name="Corte", price=Decimal("30000"))
            self.beard = ServiceFactory(name="Barba", price=Decimal("15000"))
            self.ana = ProfessionalFactory(display_name="Ana", default_commission_pct=40)
            self.luis = ProfessionalFactory(
                display_name="Luis", default_commission_pct=Decimal("35.5")
            )
            self.a1 = self.appointment(
                self.ana, local(3, 2, 10), "completed", (self.cut, 30000), (self.beard, 15000)
            )
            self.a2 = self.appointment(self.ana, local(3, 2, 15), "completed", (self.cut, 30000))
            self.a3 = self.appointment(self.luis, local(3, 9, 9), "completed", (self.cut, 33333))
            self.a4 = self.appointment(self.luis, local(3, 10, 11), "cancelled", (self.cut, 30000))
            self.a5 = self.appointment(
                self.ana, local(3, 31, 23, 30), "completed", (self.beard, 15000)
            )
            self.a6 = self.appointment(self.luis, local(4, 1, 10), "no_show", (self.cut, 30000))
            self.a7 = self.appointment(self.ana, local(3, 3, 10), "rescheduled", (self.cut, 30000))

    def appointment(self, professional, start, status, *items):
        appointment = AppointmentFactory(
            professional=professional,
            start_at=start,
            end_at=start + dt.timedelta(minutes=30),
            status=status,
            price_total=sum(Decimal(price) for _, price in items),
        )
        for service, price in items:
            AppointmentItemFactory(
                appointment=appointment,
                service=service,
                price_charged=Decimal(price),
                commission_pct_snapshot=professional.default_commission_pct,
            )
        if status == "completed":
            commissions.record_for_appointment(appointment)
        return appointment

    def client(self, role="owner", professional=None):
        user = UserFactory(tenant=self.tenant, role=role)
        if professional is not None:
            with tenant_context(self.tenant):
                professional.user = user
                professional.save(update_fields=["user"])
        client = APIClient()
        login(client, user, host(self.tenant.slug))
        client.defaults["HTTP_HOST"] = host(self.tenant.slug)
        return client
