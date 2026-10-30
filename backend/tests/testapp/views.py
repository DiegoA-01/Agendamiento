from django.http import HttpRequest, JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import permission_for
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


class PermView(APIView):
    """Vista genérica: exige `permission_for(resource, action)` tomados de la URL."""

    schema = None  # solo de pruebas: fuera de la documentación OpenAPI

    def get_permissions(self):
        return [permission_for(self.kwargs["resource"], self.kwargs["action"])()]

    def get(self, request, resource, action):
        return Response({"ok": True})
