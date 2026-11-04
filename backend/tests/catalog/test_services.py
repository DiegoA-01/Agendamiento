"""Contrato del catálogo con el motor de disponibilidad y las citas (B4.1, spec §8)."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalog import services as catalog
from apps.tenancy.context import tenant_context
from tests.catalog.factories import (
    ProfessionalFactory,
    ProfessionalServiceFactory,
    ResourceFactory,
    ServiceFactory,
)
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant():
    tenant = TenantFactory()
    with tenant_context(tenant):
        yield tenant


def offer(professional, *services, **overrides):
    for service in services:
        ProfessionalServiceFactory(professional=professional, service=service, **overrides)


# --- get_bookable_services ----------------------------------------------------------------------


def test_bookable_services_keep_the_requested_order_without_duplicates(tenant):
    cut, beard = ServiceFactory(), ServiceFactory()
    found = catalog.get_bookable_services([beard.pk, cut.pk, str(beard.pk)])
    assert found == [beard, cut]


@pytest.mark.parametrize("problem", ["inactive", "deleted", "other_tenant", "not_uuid", "empty"])
def test_bookable_services_reject_the_whole_list_if_one_is_not_bookable(tenant, problem):
    ok = ServiceFactory()
    if problem == "inactive":
        bad = ServiceFactory(is_active=False).pk
    elif problem == "deleted":
        bad = ServiceFactory(deleted_at=timezone.now()).pk
    elif problem == "other_tenant":
        with tenant_context(TenantFactory()):
            bad = ServiceFactory().pk
    elif problem == "not_uuid":
        bad = "no-es-un-uuid"
    ids = [] if problem == "empty" else [ok.pk, bad]
    assert catalog.get_bookable_services(ids) is None


# --- professionals_for_services -----------------------------------------------------------------


def test_only_professionals_offering_every_service_are_candidates(tenant):
    cut, beard = ServiceFactory(), ServiceFactory()
    both = ProfessionalFactory(display_name="Bruno")
    only_cut = ProfessionalFactory(display_name="Ana")
    offer(both, cut, beard)
    offer(only_cut, cut)

    assert catalog.professionals_for_services([cut, beard]) == [both]
    assert catalog.professionals_for_services([cut]) == [only_cut, both]  # orden alfabético


def test_inactive_professionals_and_removed_offers_do_not_count(tenant):
    cut = ServiceFactory()
    inactive = ProfessionalFactory(is_active=False)
    offer(inactive, cut)
    removed = ProfessionalFactory()
    offer(removed, cut, deleted_at=timezone.now())

    assert catalog.professionals_for_services([cut]) == []


def test_online_booking_only_lists_professionals_who_accept_it(tenant):
    cut = ServiceFactory()
    online, walk_in = ProfessionalFactory(), ProfessionalFactory(accepts_online_booking=False)
    offer(online, cut)
    offer(walk_in, cut)

    assert set(catalog.professionals_for_services([cut])) == {online, walk_in}
    assert catalog.professionals_for_services([cut], online_only=True) == [online]


def test_professionals_of_another_tenant_are_never_candidates(tenant):
    cut = ServiceFactory()
    with tenant_context(TenantFactory()):
        offer(ProfessionalFactory(), ServiceFactory())
    assert catalog.professionals_for_services([cut]) == []


# --- quote --------------------------------------------------------------------------------------


def test_quote_uses_service_values_and_the_professional_default_commission(tenant):
    cut = ServiceFactory(price=Decimal("30000"), duration_min=30, buffer_min=5)
    beard = ServiceFactory(price=Decimal("15000.50"), duration_min=20, buffer_min=10)
    professional = ProfessionalFactory(default_commission_pct=Decimal("40"))
    offer(professional, cut, beard)

    result = catalog.quote(professional, [cut, beard])

    assert [item.service_id for item in result.items] == [cut.pk, beard.pk]
    assert [item.price for item in result.items] == [Decimal("30000.00"), Decimal("15000.50")]
    assert [item.commission_pct for item in result.items] == [Decimal("40.00")] * 2
    assert result.total_price == Decimal("45000.50")
    # 30 + 20 minutos + el buffer del ÚLTIMO servicio (10), no la suma de buffers.
    assert result.total_duration_min == 60
    assert result.professional_id == professional.pk
    assert result.requires_resource is False


def test_quote_prefers_the_professional_overrides(tenant):
    cut = ServiceFactory(price=Decimal("30000"), duration_min=30)
    professional = ProfessionalFactory(default_commission_pct=Decimal("40"))
    offer(
        professional,
        cut,
        price_override=Decimal("45000"),
        duration_override_min=45,
        commission_pct_override=Decimal("50"),
    )

    (item,) = catalog.quote(professional, [cut]).items

    assert (item.price, item.duration_min, item.commission_pct) == (
        Decimal("45000.00"),
        45,
        Decimal("50.00"),
    )


def test_a_zero_override_is_respected_and_not_ignored(tenant):
    cut = ServiceFactory(price=Decimal("30000"))
    professional = ProfessionalFactory(default_commission_pct=Decimal("40"))
    offer(professional, cut, price_override=Decimal("0"), commission_pct_override=Decimal("0"))

    (item,) = catalog.quote(professional, [cut]).items
    assert (item.price, item.commission_pct) == (Decimal("0.00"), Decimal("0.00"))


def test_quote_is_none_if_the_professional_does_not_offer_a_service(tenant):
    cut, beard = ServiceFactory(), ServiceFactory()
    professional = ProfessionalFactory()
    offer(professional, cut)

    assert catalog.quote(professional, [cut, beard]) is None
    assert catalog.quote(professional, []) is None


def test_quote_flags_services_that_need_a_workstation(tenant):
    cut, massage = ServiceFactory(), ServiceFactory(requires_resource=True)
    professional = ProfessionalFactory()
    offer(professional, cut, massage)

    assert catalog.quote(professional, [cut, massage]).requires_resource is True
    assert catalog.requires_resource([cut]) is False


# --- active_resources ---------------------------------------------------------------------------


def test_active_resources_by_location(tenant):
    chair = ResourceFactory(name="Silla 2")
    other_location = ResourceFactory(name="Silla 1")
    ResourceFactory(name="Vieja", is_active=False, location=chair.location)

    assert catalog.active_resources() == [other_location, chair]
    assert catalog.active_resources(location_id=chair.location_id) == [chair]
