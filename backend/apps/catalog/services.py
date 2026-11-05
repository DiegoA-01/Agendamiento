"""API pública de la app catalog para otras apps.

Búsquedas de lectura para `scheduling` (horarios, M4) y para el motor de disponibilidad y la
creación de citas (M5). Todas buscan dentro del tenant activo: un id de otro negocio, borrado o
inválido se trata como inexistente.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.accounts import permissions as perms
from apps.media import services as media
from config.api import ApiError

from .models import (
    Professional,
    ProfessionalService,
    ProfessionalSpecialty,
    Resource,
    Service,
    ServiceCategory,
    Specialty,
)


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True


def get_professional(professional_id) -> Professional | None:
    if not _is_uuid(professional_id):
        return None
    return Professional.objects.filter(pk=professional_id).first()


def location_in_use(location_id) -> bool:
    """Si alguna ficha vigente (profesional o puesto) usa la sede: no se puede borrar."""
    return (
        Professional.objects.filter(location_id=location_id).exists()
        or Resource.objects.filter(location_id=location_id).exists()
    )


def get_resource(resource_id) -> Resource | None:
    if not _is_uuid(resource_id):
        return None
    return Resource.objects.filter(pk=resource_id).first()


def professional_for_user(user) -> Professional | None:
    """Ficha de profesional enlazada a la cuenta, o None si la cuenta no tiene una."""
    return Professional.objects.filter(user_id=user.pk).first()


# --- Motor de disponibilidad y citas (M5) -------------------------------------------------------


def get_bookable_services(service_ids: Iterable) -> list[Service] | None:
    """Servicios activos con esos ids, en el orden pedido (sin repetidos).

    None si la lista está vacía o si algún id no existe, está inactivo o es de otro negocio: el
    llamador responde 400/404 en vez de calcular con una parte de los servicios.
    """
    ids = list(dict.fromkeys(str(value) for value in service_ids))
    if not ids or not all(_is_uuid(value) for value in ids):
        return None
    found = {str(s.pk): s for s in Service.objects.filter(pk__in=ids, is_active=True)}
    if len(found) != len(ids):
        return None
    return [found[value] for value in ids]


def professionals_for_services(
    services: list[Service], *, online_only: bool = False
) -> list[Professional]:
    """Profesionales activos que ofrecen **todos** los servicios, por orden alfabético (spec §8.2).

    `online_only=True` deja solo a quienes aceptan reservas en línea (la reserva pública).
    """
    if not services:
        return []
    service_ids = [service.pk for service in services]
    offered = Count(
        "service_links",
        filter=Q(
            service_links__service_id__in=service_ids,
            service_links__deleted_at__isnull=True,
        ),
        distinct=True,
    )
    professionals = Professional.objects.filter(is_active=True)
    if online_only:
        professionals = professionals.filter(accepts_online_booking=True)
    return list(
        professionals.annotate(offered=offered)
        .filter(offered=len(service_ids))
        .order_by("display_name", "pk")
    )


def active_services() -> list[Service]:
    """Servicios activos con su categoría e imagen, en el orden del menú (reserva pública, M6)."""
    return list(
        Service.objects.select_related("category", "image")
        .filter(is_active=True)
        .order_by("category__sort_order", "category__name", "name", "pk")
    )


def requires_resource(services: Iterable[Service]) -> bool:
    """Si la cita necesita un puesto libre además del profesional (spec §8.5)."""
    return any(service.requires_resource for service in services)


def active_resources(location_id=None) -> list[Resource]:
    """Puestos activos (de una sede, si se indica), por nombre."""
    resources = Resource.objects.filter(is_active=True)
    if location_id is not None:
        resources = resources.filter(location_id=location_id)
    return list(resources.order_by("name", "pk"))


@dataclass(frozen=True)
class QuotedItem:
    """Un servicio de la cita con lo que cobra, dura y comisiona este profesional."""

    service_id: uuid.UUID
    price: Decimal
    duration_min: int
    commission_pct: Decimal


@dataclass(frozen=True)
class Quote:
    """Lo que costaría y duraría una cita con un profesional. Se congela en `AppointmentItem`."""

    professional_id: uuid.UUID
    items: tuple[QuotedItem, ...]
    total_price: Decimal
    # Suma de las duraciones (con overrides) + el buffer del último servicio (spec §8.1).
    total_duration_min: int
    requires_resource: bool


def quote(professional: Professional, services: list[Service]) -> Quote | None:
    """Precio, duración y comisión de cada servicio para este profesional.

    Prioridad: el override de `ProfessionalService` y, si no hay, el valor del servicio (precio y
    duración) o el porcentaje por defecto del profesional (comisión). None si el profesional no
    ofrece alguno de los servicios.
    """
    if not services:
        return None
    links = {
        link.service_id: link
        for link in ProfessionalService.objects.filter(
            professional=professional, service__in=services
        )
    }
    if len(links) != len({service.pk for service in services}):
        return None

    items = []
    for service in services:
        link = links[service.pk]
        items.append(
            QuotedItem(
                service_id=service.pk,
                price=_money(_first(link.price_override, service.price)),
                duration_min=_first(link.duration_override_min, service.duration_min),
                commission_pct=_first(
                    link.commission_pct_override, professional.default_commission_pct
                ),
            )
        )
    return Quote(
        professional_id=professional.pk,
        items=tuple(items),
        total_price=_money(sum((item.price for item in items), Decimal("0"))),
        total_duration_min=sum(item.duration_min for item in items) + services[-1].buffer_min,
        requires_resource=requires_resource(services),
    )


def _first(override, default):
    return default if override is None else override


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --- Gestión del catálogo desde el panel (M4) ---------------------------------------------------
#
# Permisos: recurso `staff_services` de la matriz §5. Propietario y administrador hacen CRUD,
# recepción solo ve y el profesional solo ve lo propio (los servicios que ofrece). Las vistas
# revisan la acción; aquí se aplica el alcance.


def _invalid(field: str, message: str) -> ApiError:
    return ApiError("validation_error", "Datos inválidos.", 400, {field: [message]})


def not_found(entity: str) -> ApiError:
    return ApiError("not_found", f"{entity} no encontrado.", 404)


def _own_professional_id(user):
    """Ficha del profesional en sesión cuando su alcance es "solo lo propio"; None si ve todo."""
    if perms.scope_for(user.role, perms.STAFF_SERVICES, "view") != perms.OWN:
        return None
    professional = professional_for_user(user)
    # Sin ficha enlazada no tiene nada propio: un id que no existe filtra todo.
    return professional.pk if professional else uuid.UUID(int=0)


def _soft_delete(instance) -> None:
    instance.deleted_at = timezone.now()
    instance.save(update_fields=["deleted_at", "updated_at"])


# Categorías


def list_categories(user) -> QuerySet[ServiceCategory]:
    categories = ServiceCategory.objects.order_by("sort_order", "name", "pk")
    own = _own_professional_id(user)
    if own is not None:
        categories = categories.filter(
            services__professional_links__professional_id=own,
            services__professional_links__deleted_at__isnull=True,
            services__deleted_at__isnull=True,
        ).distinct()
    return categories


def get_category(user, category_id) -> ServiceCategory:
    if not _is_uuid(category_id):
        raise not_found("Categoría")
    category = list_categories(user).filter(pk=category_id).first()
    if category is None:
        raise not_found("Categoría")
    return category


def create_category(*, name: str, sort_order: int = 0) -> ServiceCategory:
    return ServiceCategory.objects.create(name=name, sort_order=sort_order)


def update_category(category: ServiceCategory, **changes) -> ServiceCategory:
    for field in ("name", "sort_order"):
        if field in changes:
            setattr(category, field, changes[field])
    category.save()
    return category


def delete_category(category: ServiceCategory) -> None:
    """Borrado lógico. Una categoría con servicios vigentes no se borra: se mueven antes."""
    if Service.objects.filter(category=category).exists():
        raise ApiError(
            "category_in_use",
            "La categoría tiene servicios: muévelos o elimínalos antes.",
            409,
        )
    _soft_delete(category)


# Servicios


def list_services(user, *, category_id=None, is_active: bool | None = None) -> QuerySet[Service]:
    services = Service.objects.select_related("category", "image").order_by(
        "category__sort_order", "category__name", "name", "pk"
    )
    own = _own_professional_id(user)
    if own is not None:
        services = services.filter(
            professional_links__professional_id=own,
            professional_links__deleted_at__isnull=True,
        ).distinct()
    if category_id is not None:
        if not _is_uuid(category_id):
            return services.none()
        services = services.filter(category_id=category_id)
    if is_active is not None:
        services = services.filter(is_active=is_active)
    return services


def get_service(user, service_id) -> Service:
    if not _is_uuid(service_id):
        raise not_found("Servicio")
    service = list_services(user).filter(pk=service_id).first()
    if service is None:
        raise not_found("Servicio")
    return service


def _apply_service_changes(service: Service, changes: dict) -> None:
    if "category_id" in changes:
        category = ServiceCategory.objects.filter(pk=changes.pop("category_id")).first()
        if category is None:
            raise _invalid("category_id", "La categoría no existe.")
        service.category = category
    if "image_id" in changes:
        image_id = changes.pop("image_id")
        image = None if image_id is None else media.get_media(image_id)
        if image_id is not None and image is None:
            raise _invalid("image_id", "La imagen no existe.")
        service.image = image
    for field in (
        "name",
        "description",
        "duration_min",
        "buffer_min",
        "price",
        "is_active",
        "requires_resource",
    ):
        if field in changes:
            setattr(service, field, changes[field])


def create_service(**data) -> Service:
    service = Service()
    _apply_service_changes(service, data)
    service.save()
    return service


def update_service(service: Service, **changes) -> Service:
    _apply_service_changes(service, changes)
    service.save()
    return service


@transaction.atomic
def delete_service(service: Service) -> None:
    """Borrado lógico del servicio y de su oferta en cada profesional. Las citas pasadas lo
    conservan (su `AppointmentItem` guarda precio y duración)."""
    ProfessionalService.objects.filter(service=service).update(deleted_at=timezone.now())
    _soft_delete(service)


# Puestos


def _require_all_scope(user) -> None:
    """Los puestos no tienen "lo propio": quien solo ve lo suyo no los gestiona."""
    if perms.scope_for(user.role, perms.STAFF_SERVICES, "view") != perms.ALL:
        raise ApiError("permission_denied", "No tienes permiso para esta acción.", 403)


def list_resources(user) -> QuerySet[Resource]:
    _require_all_scope(user)
    return Resource.objects.select_related("location").order_by("name", "pk")


def get_resource_for(user, resource_id) -> Resource:
    resource = (
        list_resources(user).filter(pk=resource_id).first() if _is_uuid(resource_id) else None
    )
    if resource is None:
        raise not_found("Puesto")
    return resource


def _location_or_default(tenant, location_id):
    from apps.company import services as company  # company importa este módulo

    if location_id is None:
        return company.get_default_location(tenant)
    location = company.find_location(location_id)
    if location is None:
        raise _invalid("location_id", "La sede no existe.")
    return location


def create_resource(tenant, *, name: str, kind: str = "", is_active: bool = True, location_id=None):
    return Resource.objects.create(
        location=_location_or_default(tenant, location_id),
        name=name,
        kind=kind,
        is_active=is_active,
    )


def update_resource(tenant, resource: Resource, **changes) -> Resource:
    if "location_id" in changes:
        resource.location = _location_or_default(tenant, changes.pop("location_id"))
    for field in ("name", "kind", "is_active"):
        if field in changes:
            setattr(resource, field, changes[field])
    resource.save()
    return resource


def delete_resource(resource: Resource) -> None:
    _soft_delete(resource)


# Especialidades


def list_specialties() -> QuerySet[Specialty]:
    return Specialty.objects.order_by("name", "pk")


def get_specialty(specialty_id) -> Specialty:
    specialty = (
        list_specialties().filter(pk=specialty_id).first() if _is_uuid(specialty_id) else None
    )
    if specialty is None:
        raise not_found("Especialidad")
    return specialty


def create_specialty(*, name: str) -> Specialty:
    return Specialty.objects.create(name=name)


def update_specialty(specialty: Specialty, *, name: str) -> Specialty:
    specialty.name = name
    specialty.save()
    return specialty


@transaction.atomic
def delete_specialty(specialty: Specialty) -> None:
    ProfessionalSpecialty.objects.filter(specialty=specialty).delete()
    _soft_delete(specialty)


# Equipo (profesionales)


def list_professionals(user) -> QuerySet[Professional]:
    professionals = Professional.objects.select_related("photo", "location").order_by(
        "display_name", "pk"
    )
    own = _own_professional_id(user)
    if own is not None:
        professionals = professionals.filter(pk=own)
    return professionals


def get_professional_for(user, professional_id) -> Professional:
    professional = (
        list_professionals(user).filter(pk=professional_id).first()
        if _is_uuid(professional_id)
        else None
    )
    if professional is None:
        raise not_found("Profesional")
    return professional


def with_specialties(professionals: Iterable[Professional]) -> list[Professional]:
    """Agrega `specialty_id_list` a cada ficha (para serializar) con una sola consulta."""
    professionals = list(professionals)
    by_professional: dict[uuid.UUID, list[uuid.UUID]] = {p.pk: [] for p in professionals}
    links = ProfessionalSpecialty.objects.filter(professional__in=professionals).order_by(
        "specialty__name"
    )
    for professional_id, specialty_id in links.values_list("professional_id", "specialty_id"):
        by_professional[professional_id].append(specialty_id)
    for professional in professionals:
        professional.specialty_id_list = by_professional[professional.pk]
    return professionals


def _set_specialties(professional: Professional, ids: list) -> None:
    wanted = list(dict.fromkeys(ids))
    found = set(Specialty.objects.filter(pk__in=wanted).values_list("pk", flat=True))
    if len(found) != len(wanted):
        raise _invalid("specialty_ids", "Alguna especialidad no existe.")
    ProfessionalSpecialty.objects.filter(professional=professional).exclude(
        specialty_id__in=wanted
    ).delete()
    current = set(
        ProfessionalSpecialty.objects.filter(professional=professional).values_list(
            "specialty_id", flat=True
        )
    )
    for specialty_id in wanted:
        if specialty_id not in current:
            ProfessionalSpecialty.objects.create(
                professional=professional, specialty_id=specialty_id
            )


def _apply_professional_changes(tenant, professional: Professional, changes: dict) -> None:
    from apps.accounts import services as accounts  # accounts no depende de catalog

    if "user_id" in changes:
        user_id = changes.pop("user_id")
        account = None if user_id is None else accounts.get_tenant_user(tenant, user_id)
        if user_id is not None and account is None:
            raise _invalid("user_id", "La cuenta no existe en este negocio.")
        taken = (
            account is not None
            and Professional.objects.filter(user_id=account.pk).exclude(pk=professional.pk).exists()
        )
        if taken:
            raise _invalid("user_id", "Esa cuenta ya tiene una ficha de profesional.")
        professional.user = account
    if "location_id" in changes:
        professional.location = _location_or_default(tenant, changes.pop("location_id"))
    elif professional.location_id is None:
        professional.location = _location_or_default(tenant, None)
    if "photo_id" in changes:
        photo_id = changes.pop("photo_id")
        photo = None if photo_id is None else media.get_media(photo_id)
        if photo_id is not None and photo is None:
            raise _invalid("photo_id", "La imagen no existe.")
        professional.photo = photo
    for field in (
        "display_name",
        "bio",
        "default_commission_pct",
        "is_active",
        "accepts_online_booking",
    ):
        if field in changes:
            setattr(professional, field, changes[field])


@transaction.atomic
def create_professional(tenant, **data) -> Professional:
    """Alta en el equipo, dentro del límite del plan (`max_professionals`)."""
    if Professional.objects.count() >= tenant.plan.max_professionals:
        raise ApiError(
            "plan_limit_reached",
            "Tu plan no admite más profesionales.",
            409,
            {"max_professionals": [str(tenant.plan.max_professionals)]},
        )
    specialties = data.pop("specialty_ids", None)
    professional = Professional()
    _apply_professional_changes(tenant, professional, data)
    professional.save()
    if specialties is not None:
        _set_specialties(professional, specialties)
    return professional


@transaction.atomic
def update_professional(tenant, professional: Professional, **changes) -> Professional:
    specialties = changes.pop("specialty_ids", None)
    _apply_professional_changes(tenant, professional, changes)
    professional.save()
    if specialties is not None:
        _set_specialties(professional, specialties)
    return professional


@transaction.atomic
def delete_professional(professional: Professional) -> None:
    """Borrado lógico de la ficha y de los servicios que ofrecía. Libera el cupo del plan y la
    cuenta enlazada (que puede enlazarse a otra ficha)."""
    ProfessionalService.objects.filter(professional=professional).update(deleted_at=timezone.now())
    _soft_delete(professional)


# Servicios de cada profesional (con overrides)


def list_offered_services(professional: Professional) -> QuerySet[ProfessionalService]:
    return (
        ProfessionalService.objects.filter(professional=professional)
        .select_related("service")
        .order_by("service__name", "pk")
    )


@transaction.atomic
def replace_offered_services(professional: Professional, offers: list[dict]):
    """Reemplaza la lista completa de servicios que ofrece el profesional, con sus overrides.

    Los que ya estaban se actualizan (se conserva su id), los nuevos se crean y los que faltan se
    dan de baja (borrado lógico).
    """
    ids = [offer["service_id"] for offer in offers]
    if len(set(ids)) != len(ids):
        raise _invalid("services", "Hay servicios repetidos.")
    found = set(Service.objects.filter(pk__in=ids).values_list("pk", flat=True))
    missing = [str(value) for value in ids if value not in found]
    if missing:
        raise _invalid("services", f"Servicios inexistentes: {', '.join(missing)}.")

    current = {link.service_id: link for link in list_offered_services(professional)}
    for service_id, link in current.items():
        if service_id not in found:
            link.deleted_at = timezone.now()
            link.save(update_fields=["deleted_at", "updated_at"])
    for offer in offers:
        link = current.get(offer["service_id"]) or ProfessionalService(
            professional=professional, service_id=offer["service_id"]
        )
        link.price_override = offer.get("price_override")
        link.commission_pct_override = offer.get("commission_pct_override")
        link.duration_override_min = offer.get("duration_override_min")
        link.save()
    return list_offered_services(professional)
