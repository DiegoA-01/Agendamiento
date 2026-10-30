import factory

from apps.accounts.models import User
from apps.tenancy import services
from apps.tenancy.models import Plan, Tenant

PASSWORD = "Clave-Segura-2026!"


class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan

    name = factory.Sequence(lambda n: f"Plan {n}")
    modules = factory.LazyFunction(lambda: ["booking"])


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Barbería {n}")
    slug = factory.Sequence(lambda n: f"barberia-{n}")
    plan = factory.SubFactory(PlanFactory)

    @factory.post_generation
    def with_domain(self, create, extracted, **kwargs):
        """Crea subdominio verificado y módulos del plan (desactivar con with_domain=False)."""
        if create and extracted is not False:
            services.ensure_subdomain(self)
            services.sync_modules_from_plan(self)


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
