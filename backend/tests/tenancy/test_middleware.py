import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.utils import timezone

from apps.tenancy.context import get_current_tenant
from apps.tenancy.middleware import TenantMiddleware
from apps.tenancy.models import Domain
from tests.factories import TenantFactory

pytestmark = pytest.mark.django_db


def run_middleware(host: str, path: str = "/anything/"):
    """Ejecuta el middleware y devuelve (response, lo que vio la vista)."""
    seen = {}

    def view(request):
        seen["tenant"] = get_current_tenant()
        seen["request_tenant"] = request.tenant
        seen["is_platform_admin"] = request.is_platform_admin
        return HttpResponse("ok")

    request = RequestFactory().get(path, HTTP_HOST=host)
    return TenantMiddleware(view)(request), seen


def test_unknown_host_returns_404():
    response = Client().get("/test/notes/", HTTP_HOST=f"inventado.{settings.BASE_DOMAIN}")
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_host"


def test_subdomain_resolves_tenant():
    tenant = TenantFactory(slug="elfilo")
    response, seen = run_middleware(f"elfilo.{settings.BASE_DOMAIN}")
    assert response.status_code == 200
    assert seen["tenant"] == tenant
    assert seen["request_tenant"] == tenant
    assert seen["is_platform_admin"] is False


def test_host_with_port_and_uppercase_resolves():
    tenant = TenantFactory(slug="elfilo")
    _, seen = run_middleware(f"ElFilo.{settings.BASE_DOMAIN}:8080")
    assert seen["tenant"] == tenant


def test_admin_host_is_platform_context_without_tenant():
    response, seen = run_middleware(f"admin.{settings.BASE_DOMAIN}")
    assert response.status_code == 200
    assert seen["tenant"] is None
    assert seen["request_tenant"] is None
    assert seen["is_platform_admin"] is True


def test_unverified_domain_returns_404():
    tenant = TenantFactory(slug="nuevo", with_domain=False)
    Domain.objects.create(tenant=tenant, host=f"nuevo.{settings.BASE_DOMAIN}", verified=False)
    response, _ = run_middleware(f"nuevo.{settings.BASE_DOMAIN}")
    assert response.status_code == 404


def test_soft_deleted_domain_and_tenant_return_404():
    tenant = TenantFactory(slug="viejo")
    response, _ = run_middleware(f"viejo.{settings.BASE_DOMAIN}")
    assert response.status_code == 200
    type(tenant).objects.filter(pk=tenant.pk).update(deleted_at=timezone.now())
    response, _ = run_middleware(f"viejo.{settings.BASE_DOMAIN}")
    assert response.status_code == 404


def test_custom_domain_resolves_when_verified():
    tenant = TenantFactory(slug="elfilo")
    Domain.objects.create(
        tenant=tenant, host="www.elfilo.com", kind=Domain.Kind.CUSTOM, verified=True
    )
    _, seen = run_middleware("www.elfilo.com")
    assert seen["tenant"] == tenant


@pytest.mark.parametrize("path", ["/healthz/", "/api/schema/"])
def test_exempt_paths_work_on_any_host(path):
    response = Client().get(path, HTTP_HOST="cualquiera.example.org")
    assert response.status_code == 200


def test_tenant_is_cleared_after_request():
    TenantFactory(slug="elfilo")
    run_middleware(f"elfilo.{settings.BASE_DOMAIN}")
    assert get_current_tenant() is None
