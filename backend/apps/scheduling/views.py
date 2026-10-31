from zoneinfo import ZoneInfo

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from . import serializers
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
