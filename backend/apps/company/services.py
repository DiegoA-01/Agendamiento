"""API pública de la app company. M4 agrega edición y sedes."""

from apps.tenancy import services as tenancy

from .models import Company, Location

# Nombre de la sede que se crea con el negocio, en su idioma. El propietario puede cambiarlo.
DEFAULT_LOCATION_NAME = {"es": "Sede principal", "en": "Main location"}


def create_company(tenant, *, trade_name: str = "") -> Company:
    """Crea la empresa del tenant con el nombre comercial inicial y su sede por defecto.

    La sede hace falta desde el primer día: profesionales y puestos exigen una. Corre dentro del
    tenant porque las tablas tienen RLS.
    """
    with tenancy.tenant_context(tenant):
        created = Company.objects.create(trade_name=trade_name or tenant.name)
        Location.objects.create(
            name=DEFAULT_LOCATION_NAME.get(tenant.language, DEFAULT_LOCATION_NAME["es"]),
            is_default=True,
        )
        return created


def get_company(tenant) -> Company | None:
    with tenancy.tenant_context(tenant):
        return Company.objects.first()


def get_default_location(tenant) -> Location | None:
    """Sede por defecto del negocio (el MVP usa solo esa)."""
    with tenancy.tenant_context(tenant):
        return Location.objects.filter(is_default=True).first()
