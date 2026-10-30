import pytest
from rest_framework.test import APIClient

from tests.accounts.helpers import ADMIN_HOST
from tests.factories import PlanFactory, SuperadminFactory

from .fakes import FakeResolver


@pytest.fixture(autouse=True)
def fake_dns(settings):
    """Los tests nunca salen a internet: el DNS es una clase falsa que cada test configura."""
    settings.DNS_RESOLVER = "tests.platform_admin.fakes.FakeResolver"
    FakeResolver.reset()
    yield FakeResolver
    FakeResolver.reset()


@pytest.fixture
def root():
    return SuperadminFactory(email="root@demo.com")


@pytest.fixture
def api(root):
    """Cliente con sesión de Super Admin (el 2FA ya se prueba en tests/accounts)."""
    client = APIClient()
    client.force_login(root)
    return client


@pytest.fixture
def plan():
    return PlanFactory(name="Profesional", modules=["booking", "commissions"])


def call(client: APIClient, method: str, path: str, data=None, host: str = ADMIN_HOST):
    return getattr(client, method)(path, data, format="json", HTTP_HOST=host)


def new_tenant_payload(plan, **overrides) -> dict:
    payload = {
        "name": "Barbería El Filo",
        "slug": "elfilo",
        "plan_id": str(plan.pk),
        "owner_email": "dueno@elfilo.com",
        "owner_name": "Diego Dueño",
    }
    return {**payload, **overrides}
