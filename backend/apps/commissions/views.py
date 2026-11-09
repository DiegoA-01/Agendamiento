from zoneinfo import ZoneInfo

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_COMMISSIONS
from config.api import ApiError
from config.csv import csv_response

from . import serializers
from . import services as commissions


class IsTenantUser(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(request, "tenant", None))


class ModuleView(APIView):
    """Base para comisiones y reportes: exige el módulo del plan y trabaja en la zona horaria del
    negocio (las fechas `from`/`to` son días locales)."""

    permission_classes = [IsTenantUser]
    module = MODULE_COMMISSIONS

    def dispatch(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return super().dispatch(request, *args, **kwargs)
        with timezone.override(ZoneInfo(tenant.timezone)):
            return super().dispatch(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not tenancy.is_module_enabled(request.tenant, self.module):
            raise ApiError("module_disabled", f"El módulo '{self.module}' no está habilitado.", 403)


RANGE_PARAMETERS = [
    OpenApiParameter(
        "from",
        OpenApiTypes.DATE,
        description="Primer día (hora local). Por defecto, inicio del mes.",
    ),
    OpenApiParameter(
        "to", OpenApiTypes.DATE, description="Último día, incluido. Por defecto, fin del mes."
    ),
    OpenApiParameter("professional_id", OpenApiTypes.UUID),
    OpenApiParameter("service_id", OpenApiTypes.UUID),
    OpenApiParameter("category_id", OpenApiTypes.UUID),
]
COMMISSION_PARAMETERS = [
    *RANGE_PARAMETERS,
    OpenApiParameter("kind", str, enum=["entry", "adjustment"]),
]
CSV_RESPONSE = OpenApiResponse(OpenApiTypes.BINARY, description="Archivo CSV (UTF-8 con BOM).")


class ByAppointmentDatePagination(CursorPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    ordering = ("appointment_start_at", "created_at", "id")


def filtered_entries(request):
    query = serializers.CommissionQuerySerializer.from_request(request, kind=None)
    query.is_valid(raise_exception=True)
    data = query.validated_data
    start_at, end_at = commissions.local_range(data["start"], data["end"])
    return commissions.entries_for(
        request.user,
        start_at=start_at,
        end_at=end_at,
        professional_id=data.get("professional_id"),
        service_id=data.get("service_id"),
        category_id=data.get("category_id"),
        kind=data.get("kind"),
    )


class CommissionListView(ModuleView):
    @extend_schema(
        parameters=COMMISSION_PARAMETERS,
        responses=serializers.CommissionEntrySerializer(many=True),
        description="Comisiones por fecha de la cita. Un profesional solo ve las suyas.",
    )
    def get(self, request):
        entries = filtered_entries(request)
        paginator = ByAppointmentDatePagination()
        page = paginator.paginate_queryset(entries, request, view=self)
        return paginator.get_paginated_response(
            serializers.CommissionEntrySerializer(page, many=True).data
        )


class CommissionExportView(ModuleView):
    @extend_schema(parameters=COMMISSION_PARAMETERS, responses={200: CSV_RESPONSE})
    def get(self, request):
        entries = filtered_entries(request).order_by("appointment_start_at", "created_at")
        rows = (
            [
                timezone.localtime(entry.appointment_start_at).strftime("%Y-%m-%d %H:%M"),
                entry.kind,
                entry.professional.display_name,
                entry.service.name,
                entry.base_amount,
                entry.pct,
                entry.commission_amount,
                entry.business_amount,
                entry.reason,
            ]
            for entry in entries.iterator(chunk_size=500)
        )
        header = [
            "fecha_cita",
            "tipo",
            "profesional",
            "servicio",
            "valor",
            "porcentaje",
            "comision",
            "negocio",
            "motivo",
        ]
        return csv_response("comisiones.csv", header, rows)


class CommissionAdjustmentView(ModuleView):
    @extend_schema(
        request=serializers.AdjustmentCreateSerializer,
        responses={201: serializers.CommissionEntrySerializer},
        description=(
            "Corrige una comisión con los valores que debió tener. La original no cambia: se "
            "guarda la diferencia como una entrada `adjustment`. Solo el dueño."
        ),
    )
    def post(self, request, entry_id):
        commissions.require_adjust(request.user)
        entry = commissions.get_entry(request.user, entry_id)
        body = serializers.AdjustmentCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        adjustment = commissions.create_adjustment(
            entry, created_by=request.user, **body.validated_data
        )
        return Response(
            serializers.CommissionEntrySerializer(adjustment).data, status=status.HTTP_201_CREATED
        )
