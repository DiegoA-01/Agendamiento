import io
from zoneinfo import ZoneInfo

import pytest
from django.core.management import CommandError, call_command
from rest_framework.test import APIClient

from apps.booking.models import Appointment
from apps.catalog.models import Professional, ProfessionalService, Service
from apps.scheduling.models import WorkingHours
from apps.tenancy import services as tenancy
from apps.tenancy.context import tenant_context
from tests.accounts.helpers import host

pytestmark = pytest.mark.django_db

PASSWORD = "Clave-Demo-2026!"


def seed(*args) -> str:
    out = io.StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


@pytest.mark.parametrize("vertical", ["barbershop", "salon", "nails"])
def test_creates_a_complete_demo_business(vertical):
    output = seed("--vertical", vertical, "--password", PASSWORD)

    tenant = tenancy.get_tenant_by_slug(f"demo-{vertical}")
    assert tenant is not None and tenant.vertical == vertical
    assert f"propietario@demo-{vertical}.test" in output
    with tenant_context(tenant):
        assert Professional.objects.count() == 3
        assert Service.objects.count() == 6
        assert ProfessionalService.objects.count() == 6 + 6 + 4
        # Lunes a sábado, de 9:00 a 19:00, para cada profesional.
        assert WorkingHours.objects.count() == 3 * 6
        assert set(WorkingHours.objects.values_list("weekday", flat=True)) == set(range(6))
        appointments = Appointment.objects.all()
        assert appointments.count() == 6
        assert {a.status for a in appointments} == {"confirmed"}
        tz = ZoneInfo(tenant.timezone)
        assert all(a.start_at.astimezone(tz).weekday() < 6 for a in appointments)


def test_the_owner_can_sign_in_and_the_business_is_bookable():
    seed("--slug", "demo-e2e", "--password", PASSWORD)
    client = APIClient()
    at = host("demo-e2e")

    response = client.post(
        "/api/v1/auth/login/",
        {"email": "propietario@demo-e2e.test", "password": PASSWORD},
        format="json",
        HTTP_HOST=at,
    )
    assert response.status_code == 200, response.json()
    services = client.get("/api/v1/public/services/", HTTP_HOST=at).json()
    assert sum(len(category["services"]) for category in services) == 6


def test_a_random_password_is_generated_and_shown_once():
    output = seed("--slug", "demo-random")
    assert "Contraseña:" in output
    assert len(output.split("Contraseña:")[1].split()[0]) >= 12


def test_an_existing_subdomain_is_not_overwritten():
    seed("--slug", "demo-unico", "--password", PASSWORD)
    with pytest.raises(CommandError, match="demo-unico"):
        seed("--slug", "demo-unico", "--password", PASSWORD)


def test_an_unknown_vertical_is_rejected():
    with pytest.raises(CommandError):
        seed("--vertical", "spa-lunar")


def test_the_barbershop_demo_uses_the_dark_green_and_gold_theme():
    seed("--vertical", "barbershop", "--password", PASSWORD)
    seed("--vertical", "salon", "--password", PASSWORD)

    barbershop = tenancy.get_tenant_by_slug("demo-barbershop")
    assert barbershop.theme["background"] == "#0e2620"
    assert barbershop.theme["primary"] == "#d4ae63"
    # Los otros tipos de negocio siguen con el tema por defecto.
    assert tenancy.get_tenant_by_slug("demo-salon").theme.get("background", "#ffffff") == "#ffffff"
