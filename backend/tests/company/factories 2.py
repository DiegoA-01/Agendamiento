import factory

from apps.company.models import Location
from tests.tenancy.factories import TenantOwnedFactory


class LocationFactory(TenantOwnedFactory):
    class Meta:
        model = Location

    name = factory.Sequence(lambda n: f"Sede {n}")
    address = "Calle 10 # 20-30"
