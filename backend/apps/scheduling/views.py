from zoneinfo import ZoneInfo

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import permissions as perms
from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_BOOKING
from config.api import ApiError

from . import availability, serializers
from . import services as scheduling


class IsTenantUser(BasePermission):
    """Sesión iniciada en el host de un negocio. El rol se revisa en `services` (alcance)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(request, "tenant", None))


class TenantView(APIView):
    """Base de la API del negocio. Las fechas entran y salen en la zona horaria del negocio: una
    fecha sin zona se interpreta en hora local y la respuesta lleva el desfase (`-05:00`)."""

    permission_classes = [IsTenantUser]

    def dispatch(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return super().dispatch(request, *args, **kwargs)
        with timezone.override(ZoneInfo(tenant.timezone)):
            return super().dispatch(request, *args, **kwargs)


class ByStartPagination(CursorPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    ordering = ("start_at", "id")


CONFLICT_RESPONSE = OpenApiResponse(
    serializers.TimeBlockConflictSerializer,
    description="El bloqueo choca con citas activas (`time_block_conflict`).",
)


class AgendaSettingsView(TenantView):
    """Reglas de agenda del negocio. Son datos de la empresa: el propietario las edita y el
    administrador las ve (matriz §5)."""

    def get_permissions(self):
        action = "view" if self.request.method == "GET" else "update"
        return [IsTenantUser(), perms.permission_for(perms.COMPANY, action)()]

    @extend_schema(responses=serializers.AgendaSettingsSerializer)
    def get(self, request):
        return Response(tenancy.agenda_settings(request.tenant))

    @extend_schema(
        request=serializers.AgendaSettingsSerializer(partial=True),
        responses=serializers.AgendaSettingsSerializer,
    )
    def patch(self, request):
        data = serializers.AgendaSettingsSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        return Response(tenancy.update_agenda_settings(request.tenant, **data.validated_data))


class WorkingHoursView(TenantView):
    @extend_schema(responses=serializers.WorkingHoursSerializer(many=True))
    def get(self, request, professional_id):
        professional = scheduling.professional_for(request.user, professional_id)
        hours = scheduling.get_working_hours(professional)
        return Response(serializers.WorkingHoursSerializer(hours, many=True).data)

    @extend_schema(
        description="Reemplaza la semana completa. Una lista vacía deja al profesional sin "
        "horario. Varias franjas el mismo día representan un descanso.",
        request=serializers.WorkingHoursSerializer(many=True),
        responses=serializers.WorkingHoursSerializer(many=True),
    )
    def put(self, request, professional_id):
        professional = scheduling.professional_for(request.user, professional_id, "update")
        data = serializers.WorkingHoursSerializer(data=request.data, many=True)
        data.is_valid(raise_exception=True)
        hours = scheduling.replace_working_hours(professional, data.validated_data)
        return Response(serializers.WorkingHoursSerializer(hours, many=True).data)


class TimeBlockListCreateView(TenantView):
    @extend_schema(
        parameters=[
            OpenApiParameter("professional_id", str),
            OpenApiParameter("resource_id", str),
            OpenApiParameter("start_at", str, description="Bloqueos que terminan después de"),
            OpenApiParameter("end_at", str, description="Bloqueos que empiezan antes de"),
        ],
        responses=serializers.TimeBlockSerializer(many=True),
    )
    def get(self, request):
        filters = serializers.TimeBlockFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        blocks = scheduling.list_time_blocks(request.user, **filters.validated_data)
        paginator = ByStartPagination()
        page = paginator.paginate_queryset(blocks, request, view=self)
        return paginator.get_paginated_response(
            serializers.TimeBlockSerializer(page, many=True).data
        )

    @extend_schema(
        request=serializers.TimeBlockCreateSerializer,
        responses={201: serializers.TimeBlockSerializer, 409: CONFLICT_RESPONSE},
    )
    def post(self, request):
        data = serializers.TimeBlockCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        block = scheduling.create_time_block(request.user, **data.validated_data)
        return Response(serializers.TimeBlockSerializer(block).data, status=status.HTTP_201_CREATED)


class TimeBlockDetailView(TenantView):
    @extend_schema(responses=serializers.TimeBlockSerializer)
    def get(self, request, block_id):
        block = scheduling.get_time_block(request.user, block_id)
        return Response(serializers.TimeBlockSerializer(block).data)

    @extend_schema(
        request=serializers.TimeBlockUpdateSerializer,
        responses={200: serializers.TimeBlockSerializer, 409: CONFLICT_RESPONSE},
    )
    def patch(self, request, block_id):
        data = serializers.TimeBlockUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        block = scheduling.update_time_block(request.user, block_id, **data.validated_data)
        return Response(serializers.TimeBlockSerializer(block).data)

    @extend_schema(responses={204: None})
    def delete(self, request, block_id):
        scheduling.delete_time_block(request.user, block_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvailabilityView(TenantView):
    """Horarios libres para agendar desde el panel. Exige el módulo `booking` y poder crear citas;
    la reserva pública (M6) usa el mismo motor con las reglas del negocio."""

    def get_permissions(self):
        return [IsTenantUser(), perms.permission_for(perms.APPOINTMENTS, "create")()]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not tenancy.is_module_enabled(request.tenant, MODULE_BOOKING):
            raise ApiError("module_disabled", "El módulo 'booking' no está habilitado.", 403)

    def query(self, serializer_class):
        params = self.request.query_params
        data = {**params.dict(), "service_ids": params.getlist("service_ids")}
        query = serializer_class(data=data)
        query.is_valid(raise_exception=True)
        return query.validated_data


AVAILABILITY_PARAMS = [
    OpenApiParameter("service_ids", str, many=True, required=True),
    OpenApiParameter("professional_id", str, description="Vacío = cualquiera"),
]


class AvailabilitySlotsView(AvailabilityView):
    @extend_schema(
        parameters=[*AVAILABILITY_PARAMS, OpenApiParameter("date", str, required=True)],
        responses=serializers.SlotSerializer(many=True),
    )
    def get(self, request):
        query = self.query(serializers.SlotsQuerySerializer)
        slots = availability.get_available_slots(
            request.tenant,
            query["service_ids"],
            query["date"],
            query["professional_id"],
            public=False,
        )
        return Response(serializers.SlotSerializer(slots, many=True).data)


class AvailabilityDaysView(AvailabilityView):
    @extend_schema(
        parameters=[*AVAILABILITY_PARAMS, OpenApiParameter("month", str, required=True)],
        responses=serializers.DaysSerializer,
    )
    def get(self, request):
        query = self.query(serializers.DaysQuerySerializer)
        year, month = (int(part) for part in query["month"].split("-"))
        days = availability.get_available_days(
            request.tenant,
            query["service_ids"],
            year,
            month,
            query["professional_id"],
            public=False,
        )
        return Response({"days": days})
