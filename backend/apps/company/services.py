"""API pública de la app company. M4 agrega edición y sedes."""

from apps.tenancy import services as tenancy

from .models import Company


def create_company(tenant, *, trade_name: str = "") -> Company:
    """Crea la empresa del tenant con el nombre comercial inicial. Corre dentro del tenant porque
    la tabla tiene RLS."""
    with tenancy.tenant_context(tenant):
        return Company.objects.create(trade_name=trade_name or tenant.name)


def get_company(tenant) -> Company | None:
    with tenancy.tenant_context(tenant):
        return Company.objects.first()
