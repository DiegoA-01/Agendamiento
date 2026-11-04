import pytest
from django.db import IntegrityError, transaction

from apps.tenancy.context import tenant_context
from tests.catalog.factories import ProfessionalFactory, ResourceFactory
from tests.scheduling.factories import TimeBlockFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant():
    tenant = TenantFactory()
    with tenant_context(tenant):
        yield tenant


def test_a_time_block_belongs_to_a_professional_or_a_resource(tenant):
    TimeBlockFactory()
    TimeBlockFactory(professional=None, resource=ResourceFactory())


@pytest.mark.parametrize("with_professional, with_resource", [(True, True), (False, False)])
def test_a_time_block_needs_exactly_one_owner(tenant, with_professional, with_resource):
    with pytest.raises(IntegrityError), transaction.atomic():
        TimeBlockFactory(
            professional=ProfessionalFactory() if with_professional else None,
            resource=ResourceFactory() if with_resource else None,
        )
