import factory

from apps.accounts.models import User
from tests.tenancy.factories import TenantFactory

PASSWORD = "Clave-Segura-2026!"


class UserFactory(factory.django.DjangoModelFactory):
    """Usuario de un tenant (por defecto recepcionista). La contraseña es `PASSWORD`."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"usuario{n}@example.com")
    full_name = "Usuario de Prueba"
    role = User.Role.RECEPTIONIST
    tenant = factory.SubFactory(TenantFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", PASSWORD)
        return model_class.objects.create_user(password=password, **kwargs)


class SuperadminFactory(UserFactory):
    role = User.Role.SUPERADMIN
    tenant = None
