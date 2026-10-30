import factory

from apps.tenancy import services
from apps.tenancy.context import get_current_tenant, tenant_context
from apps.tenancy.models import Plan, Tenant


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


class TenantOwnedFactory(factory.django.DjangoModelFactory):
    """Base de las factories de modelos de negocio.

    Usa el tenant activo (o uno nuevo) y crea el registro dentro de su contexto, para que RLS
    acepte el INSERT. Las SubFactory de modelos de negocio deben compartir el tenant:
    `factory.SubFactory(OtraFactory, tenant=factory.SelfAttribute("..tenant"))`.
    """

    class Meta:
        abstract = True

    tenant = factory.LazyFunction(lambda: get_current_tenant() or TenantFactory())

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        with tenant_context(kwargs["tenant"]):
            return super()._create(model_class, *args, **kwargs)
