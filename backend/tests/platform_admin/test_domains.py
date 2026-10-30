import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.platform_admin.models import AuditLog
from apps.tenancy.models import Domain
from tests.factories import TenantFactory

from .conftest import call

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant(plan):
    return TenantFactory(slug="elfilo", plan=plan)


def domains_url(tenant, domain=None, suffix=""):
    base = f"/api/v1/tenants/{tenant.pk}/domains/"
    return f"{base}{domain['id']}/{suffix}" if domain else base


def add(api, tenant, host="www.elfilo.com"):
    return call(api, "post", domains_url(tenant), {"host": host})


def resolves(host: str) -> bool:
    """¿El host abre el negocio? (404 = host desconocido)"""
    return APIClient().get("/api/v1/auth/csrf/", HTTP_HOST=host).status_code == 204


def test_new_domain_comes_unverified_with_dns_instructions(api, tenant):
    response = add(api, tenant)
    assert response.status_code == 201
    body = response.json()
    assert (body["host"], body["kind"], body["verified"]) == ("www.elfilo.com", "custom", False)
    assert body["instructions"]["txt"] == {
        "name": "_agenda-challenge.www.elfilo.com",
        "value": body["verification_token"],
    }
    assert body["instructions"]["cname"] == {
        "name": "www.elfilo.com",
        "target": f"elfilo.{settings.BASE_DOMAIN}",
    }
    assert not resolves("www.elfilo.com")  # sin verificar no resuelve


def test_list_shows_the_base_subdomain_and_custom_domains(api, tenant):
    add(api, tenant)
    hosts = [d["host"] for d in call(api, "get", domains_url(tenant)).json()]
    assert hosts == [f"elfilo.{settings.BASE_DOMAIN}", "www.elfilo.com"]


def test_verifying_with_the_right_txt_record_makes_the_domain_work(api, tenant, fake_dns):
    domain = add(api, tenant).json()
    fake_dns.txt_records[domain["instructions"]["txt"]["name"]] = [domain["verification_token"]]
    fake_dns.cname_records["www.elfilo.com"] = [f"elfilo.{settings.BASE_DOMAIN}"]

    response = call(api, "post", domains_url(tenant, domain, "verify/"))
    assert response.status_code == 200
    assert response.json() == {"verified": True, "txt_ok": True, "cname_ok": True}
    assert resolves("www.elfilo.com")
    entry = AuditLog.objects.get(action="domain.verify")
    assert entry.after["verified"] is True and entry.tenant == tenant


def test_txt_alone_verifies_and_cname_is_only_reported(api, tenant, fake_dns):
    domain = add(api, tenant).json()
    fake_dns.txt_records[domain["instructions"]["txt"]["name"]] = [
        "otro-valor",
        domain["verification_token"],
    ]
    body = call(api, "post", domains_url(tenant, domain, "verify/")).json()
    assert body == {"verified": True, "txt_ok": True, "cname_ok": False}


@pytest.mark.parametrize("txt", [[], ["token-equivocado"]])
def test_wrong_or_missing_txt_does_not_verify(api, tenant, fake_dns, txt):
    domain = add(api, tenant).json()
    fake_dns.txt_records[domain["instructions"]["txt"]["name"]] = txt
    body = call(api, "post", domains_url(tenant, domain, "verify/")).json()
    assert body["verified"] is False and body["txt_ok"] is False
    assert not resolves("www.elfilo.com")


def test_token_of_another_domain_cannot_verify_this_one(api, tenant, fake_dns):
    first = add(api, tenant, "uno.com").json()
    second = add(api, tenant, "dos.com").json()
    fake_dns.txt_records["_agenda-challenge.dos.com"] = [first["verification_token"]]
    body = call(api, "post", domains_url(tenant, second, "verify/")).json()
    assert body["verified"] is False


def test_dns_failure_is_a_retryable_503_and_does_not_verify(api, tenant, fake_dns):
    domain = add(api, tenant).json()
    fake_dns.fail = True
    response = call(api, "post", domains_url(tenant, domain, "verify/"))
    assert response.status_code == 503
    assert response.json()["code"] == "dns_lookup_failed"
    assert not Domain.objects.get(pk=domain["id"]).verified


def test_cname_lookup_failure_does_not_block_a_valid_txt(api, tenant, fake_dns):
    domain = add(api, tenant).json()
    fake_dns.txt_records[domain["instructions"]["txt"]["name"]] = [domain["verification_token"]]
    fake_dns.fail_cname = True
    body = call(api, "post", domains_url(tenant, domain, "verify/")).json()
    assert body == {"verified": True, "txt_ok": True, "cname_ok": False}


@pytest.mark.parametrize(
    ("host", "code"),
    [
        ("no es un host", "invalid_host"),
        ("sinpunto", "invalid_host"),
        ("https://www.elfilo.com", "invalid_host"),
        (settings.BASE_DOMAIN, "reserved_host"),
        (f"otro.{settings.BASE_DOMAIN}", "reserved_host"),
        (f"admin.{settings.BASE_DOMAIN}", "reserved_host"),
    ],
)
def test_invalid_or_platform_hosts_are_rejected(api, tenant, host, code):
    response = add(api, tenant, host)
    assert response.status_code == 400
    assert response.json()["code"] == code


def test_a_host_cannot_be_registered_twice_even_by_another_business(api, tenant, plan):
    other = TenantFactory(slug="aura", plan=plan)
    assert add(api, tenant).status_code == 201
    again = add(api, other, "WWW.ElFilo.com.")
    assert again.status_code == 409 and again.json()["code"] == "host_taken"


def test_removing_a_custom_domain_stops_it_resolving(api, tenant, fake_dns):
    domain = add(api, tenant).json()
    fake_dns.txt_records[domain["instructions"]["txt"]["name"]] = [domain["verification_token"]]
    call(api, "post", domains_url(tenant, domain, "verify/"))
    assert resolves("www.elfilo.com")

    assert call(api, "delete", domains_url(tenant, domain)).status_code == 204
    assert not resolves("www.elfilo.com")
    assert add(api, tenant).status_code == 201  # el host queda libre otra vez


def test_the_base_subdomain_cannot_be_removed(api, tenant):
    base = call(api, "get", domains_url(tenant)).json()[0]
    response = call(api, "delete", domains_url(tenant, base))
    assert response.status_code == 400
    assert response.json()["code"] == "cannot_delete_subdomain"
    assert resolves(f"elfilo.{settings.BASE_DOMAIN}")


def test_a_domain_cannot_be_managed_through_another_tenant(api, tenant, plan):
    other = TenantFactory(slug="aura", plan=plan)
    domain = add(api, tenant).json()
    assert call(api, "delete", domains_url(other, domain)).status_code == 404
    assert call(api, "post", domains_url(other, domain, "verify/")).status_code == 404
    assert Domain.objects.filter(pk=domain["id"]).exists()
