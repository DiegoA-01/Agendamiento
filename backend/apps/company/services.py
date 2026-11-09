"""API pública de la app company: datos de la empresa y sedes."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog import services as catalog
from apps.media import services as media
from apps.tenancy import services as tenancy
from config.api import ApiError

from .models import Company, Location
from .sanitize import clean_html

# Nombre de la sede que se crea con el negocio, en su idioma. El propietario puede cambiarlo.
DEFAULT_LOCATION_NAME = {"es": "Sede principal", "en": "Main location"}

HTML_FIELDS = ("terms_html", "privacy_html", "cookies_html")
EDITABLE_FIELDS = (
    "legal_name",
    "trade_name",
    "tax_id",
    "address",
    "city",
    "phone",
    "email",
    "social_links",
    *HTML_FIELDS,
)


def create_company(tenant, *, trade_name: str = "", tax_id: str = "") -> Company:
    """Crea la empresa del tenant con el nombre comercial inicial y su sede por defecto.

    La sede hace falta desde el primer día: profesionales y puestos exigen una. Corre dentro del
    tenant porque las tablas tienen RLS.
    """
    with tenancy.tenant_context(tenant):
        created = Company.objects.create(trade_name=trade_name or tenant.name, tax_id=tax_id)
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


# --- Empresa (dentro del tenant de la petición) -------------------------------------------------


def current_company() -> Company:
    company = Company.objects.select_related("logo").first()
    if company is None:
        raise ApiError("not_found", "El negocio no tiene datos de empresa.", 404)
    return company


def update_company(company: Company, **changes: Any) -> Company:
    """Edita los datos de la empresa. El HTML legal se limpia antes de guardarlo y el logo debe
    ser una imagen del mismo negocio (`logo_id=None` lo quita)."""
    if "logo_id" in changes:
        logo_id = changes.pop("logo_id")
        logo = None if logo_id is None else media.get_media(logo_id)
        if logo_id is not None and logo is None:
            raise ApiError(
                "validation_error", "Datos inválidos.", 400, {"logo_id": ["La imagen no existe."]}
            )
        company.logo = logo
    for field in EDITABLE_FIELDS:
        if field in changes:
            value = changes[field]
            setattr(company, field, clean_html(value) if field in HTML_FIELDS else value)
    company.save()
    return company


# --- Sedes --------------------------------------------------------------------------------------


def list_locations():
    return Location.objects.order_by("-is_default", "name", "pk")


def find_location(location_id) -> Location | None:
    """Sede vigente del tenant activo, o None (también si el id es inválido o de otro negocio)."""
    try:
        return Location.objects.filter(pk=location_id).first()
    except (ValidationError, ValueError, TypeError):
        return None


def get_location(location_id) -> Location:
    location = find_location(location_id)
    if location is None:
        raise ApiError("not_found", "Sede no encontrada.", 404)
    return location


@transaction.atomic
def _make_default(location: Location) -> None:
    Location.objects.filter(is_default=True).exclude(pk=location.pk).update(is_default=False)
    location.is_default = True
    location.save()


def create_location(tenant, *, name: str, address: str = "", is_default: bool = False) -> Location:
    """Nueva sede, dentro del límite del plan (`max_locations`)."""
    if Location.objects.count() >= tenant.plan.max_locations:
        raise ApiError(
            "plan_limit_reached",
            "Tu plan no admite más sedes.",
            409,
            {"max_locations": [str(tenant.plan.max_locations)]},
        )
    with transaction.atomic():
        location = Location.objects.create(name=name, address=address)
        if is_default:
            _make_default(location)
    return location


def update_location(location: Location, **changes: Any) -> Location:
    """Edita una sede. Siempre hay exactamente una por defecto: se puede elegir otra, pero no
    dejar al negocio sin ninguna."""
    is_default = changes.pop("is_default", None)
    if is_default is False and location.is_default:
        raise ApiError(
            "default_location_required",
            "Debe haber una sede por defecto: marca otra como principal.",
            400,
            {"is_default": ["Marca otra sede como principal."]},
        )
    for field in ("name", "address"):
        if field in changes:
            setattr(location, field, changes[field])
    with transaction.atomic():
        location.save()
        if is_default and not location.is_default:
            _make_default(location)
    return location


def delete_location(location: Location) -> None:
    """Borrado lógico. No se borra la sede por defecto ni una que use alguna ficha."""
    if location.is_default:
        raise ApiError(
            "default_location_required", "No se puede eliminar la sede por defecto.", 409
        )
    if catalog.location_in_use(location.pk):
        raise ApiError(
            "location_in_use",
            "La sede tiene profesionales o puestos: muévelos a otra sede antes de eliminarla.",
            409,
        )
    location.deleted_at = timezone.now()
    location.save()
