from decimal import Decimal

import factory

from apps.catalog.models import (
    Professional,
    ProfessionalService,
    Resource,
    Service,
    ServiceCategory,
    Specialty,
)
from tests.company.factories import LocationFactory
from tests.tenancy.factories import TenantOwnedFactory

SAME_TENANT = factory.SelfAttribute("..tenant")


class ServiceCategoryFactory(TenantOwnedFactory):
    class Meta:
        model = ServiceCategory

    name = factory.Sequence(lambda n: f"Categoría {n}")


class ServiceFactory(TenantOwnedFactory):
    class Meta:
        model = Service

    category = factory.SubFactory(ServiceCategoryFactory, tenant=SAME_TENANT)
    name = factory.Sequence(lambda n: f"Corte {n}")
    duration_min = 30
    price = Decimal("30000.00")


class SpecialtyFactory(TenantOwnedFactory):
    class Meta:
        model = Specialty

    name = factory.Sequence(lambda n: f"Especialidad {n}")


class ProfessionalFactory(TenantOwnedFactory):
    class Meta:
        model = Professional

    location = factory.SubFactory(LocationFactory, tenant=SAME_TENANT)
    display_name = factory.Sequence(lambda n: f"Profesional {n}")
    default_commission_pct = Decimal("40.00")


class ProfessionalServiceFactory(TenantOwnedFactory):
    class Meta:
        model = ProfessionalService

    professional = factory.SubFactory(ProfessionalFactory, tenant=SAME_TENANT)
    service = factory.SubFactory(ServiceFactory, tenant=SAME_TENANT)


class ResourceFactory(TenantOwnedFactory):
    class Meta:
        model = Resource

    location = factory.SubFactory(LocationFactory, tenant=SAME_TENANT)
    name = factory.Sequence(lambda n: f"Silla {n}")
