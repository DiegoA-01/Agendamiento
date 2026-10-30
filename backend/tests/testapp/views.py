from django.http import HttpRequest, JsonResponse

from apps.tenancy.constants import MODULE_BOOKING
from apps.tenancy.decorators import requires_module

from .models import Note


def notes(request: HttpRequest) -> JsonResponse:
    """Lista con el manager por defecto (filtra por tenant)."""
    return JsonResponse({"notes": sorted(Note.objects.values_list("text", flat=True))})


def notes_unfiltered(request: HttpRequest) -> JsonResponse:
    """Lista con el manager SIN filtro: aquí solo protege RLS."""
    return JsonResponse({"notes": sorted(Note.all_tenants.values_list("text", flat=True))})


@requires_module(MODULE_BOOKING)
def booking_only(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True})
