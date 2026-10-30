import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from tests.accounts.factories import PASSWORD, SuperadminFactory, UserFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db


def test_email_is_normalized_and_password_is_hashed():
    user = UserFactory(email="  Camila@Ejemplo.COM ")
    assert user.email == "camila@ejemplo.com"
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)


def test_same_email_allowed_in_different_tenants():
    UserFactory(email="camila@x.com", tenant=TenantFactory())
    UserFactory(email="camila@x.com", tenant=TenantFactory())
    assert User.objects.filter(email="camila@x.com").count() == 2


def test_duplicate_email_in_same_tenant_is_rejected_ignoring_case():
    tenant = TenantFactory()
    UserFactory(email="camila@x.com", tenant=tenant)
    with pytest.raises(IntegrityError), transaction.atomic():
        UserFactory(email="CAMILA@x.com", tenant=tenant)


def test_superadmin_email_is_globally_unique():
    SuperadminFactory(email="root@x.com")
    with pytest.raises(IntegrityError), transaction.atomic():
        SuperadminFactory(email="ROOT@x.com")


def test_superadmin_and_tenant_user_may_share_an_email():
    SuperadminFactory(email="mismo@x.com")
    UserFactory(email="mismo@x.com", tenant=TenantFactory())


def test_only_superadmin_may_lack_a_tenant():
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user("a@x.com", PASSWORD, role=User.Role.OWNER, tenant=None)


def test_superadmin_cannot_belong_to_a_tenant():
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            "a@x.com", PASSWORD, role=User.Role.SUPERADMIN, tenant=TenantFactory()
        )


def test_clean_reports_role_tenant_mismatch():
    with pytest.raises(ValidationError):
        User(email="a@x.com", role=User.Role.OWNER, tenant=None).clean()


def test_for_tenant_never_mixes_tenants_and_hides_deleted():
    alfa, beta = TenantFactory(), TenantFactory()
    a = UserFactory(tenant=alfa)
    UserFactory(tenant=beta)
    root = SuperadminFactory()
    gone = UserFactory(tenant=alfa)
    User.objects.filter(pk=gone.pk).update(deleted_at=timezone.now())

    assert list(User.objects.for_tenant(alfa)) == [a]
    assert list(User.objects.for_tenant(None)) == [root]
