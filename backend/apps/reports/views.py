from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers as drf
from rest_framework.response import Response

from apps.commissions.serializers import RangeQuerySerializer
from apps.commissions.views import CSV_RESPONSE, RANGE_PARAMETERS, ModuleView
from apps.tenancy.constants import MODULE_REPORTS
from config.csv import csv_response

from . import serializers
from . import services as reports

GROUP_PARAMETER = OpenApiParameter("group_by", str, enum=list(reports.SALES_GROUPS), default="day")


class SalesQuerySerializer(RangeQuerySerializer):
    group_by = drf.ChoiceField(choices=reports.SALES_GROUPS, required=False, default="day")


def _filters(request, serializer_class=RangeQuerySerializer):
    query = serializer_class.from_request(request)
    query.is_valid(raise_exception=True)
    data = query.validated_data
    filters = reports.Filters(
        start=data["start"],
        end=data["end"],
        professional_id=data.get("professional_id"),
        service_id=data.get("service_id"),
        category_id=data.get("category_id"),
    )
    return filters, data


class ReportView(ModuleView):
    module = MODULE_REPORTS


class SalesReportView(ReportView):
    @extend_schema(
        parameters=[*RANGE_PARAMETERS, GROUP_PARAMETER],
        responses=serializers.SalesReportSerializer,
        description="Ventas de citas completadas (con ajustes de comisión incluidos).",
    )
    def get(self, request):
        filters, data = _filters(request, SalesQuerySerializer)
        report = reports.sales_report(request.user, filters, data["group_by"])
        return Response(serializers.SalesReportSerializer(report).data)


class SalesExportView(ReportView):
    @extend_schema(parameters=[*RANGE_PARAMETERS, GROUP_PARAMETER], responses={200: CSV_RESPONSE})
    def get(self, request):
        filters, data = _filters(request, SalesQuerySerializer)
        report = reports.sales_report(request.user, filters, data["group_by"])
        header = [data["group_by"], "ventas", "comisiones", "negocio", "citas", "ticket_promedio"]
        rows = [
            [
                row["label"],
                row["sales"],
                row["commissions"],
                row["business"],
                row["appointments"],
                row["average_ticket"],
            ]
            for row in [*report["rows"], {"label": "TOTAL", **report["totals"]}]
        ]
        return csv_response(f"ventas-{filters.start}-{filters.end}.csv", header, rows)


class BookingsReportView(ReportView):
    @extend_schema(
        parameters=RANGE_PARAMETERS,
        responses=serializers.BookingsReportSerializer,
        description="Reservas por mes, servicio y profesional; tasas de cancelación y no-show.",
    )
    def get(self, request):
        filters, _ = _filters(request)
        report = reports.bookings_report(request.user, filters)
        return Response(serializers.BookingsReportSerializer(report).data)


class BookingsExportView(ReportView):
    @extend_schema(parameters=RANGE_PARAMETERS, responses={200: CSV_RESPONSE})
    def get(self, request):
        filters, _ = _filters(request)
        report = reports.bookings_report(request.user, filters)
        header = [
            "agrupacion",
            "nombre",
            "total",
            "completadas",
            "canceladas",
            "no_show",
            "web",
            "tasa_cancelacion",
            "tasa_no_show",
        ]
        sections = [
            ("mes", report["by_month"]),
            ("servicio", report["by_service"]),
            ("profesional", report["by_professional"]),
            ("total", [{"label": "TOTAL", **report["totals"]}]),
        ]
        rows = [
            [
                section,
                row["label"],
                row["total"],
                row["completed"],
                row["cancelled"],
                row["no_show"],
                row["web"],
                row["cancellation_rate"],
                row["no_show_rate"],
            ]
            for section, section_rows in sections
            for row in section_rows
        ]
        return csv_response(f"reservas-{filters.start}-{filters.end}.csv", header, rows)
