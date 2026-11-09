"""Endpoints públicos (spec §9): sin sesión, el negocio sale del host."""

from collections import OrderedDict
from zoneinfo import ZoneInfo

from django.db.models import prefetch_related_objects
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog import services as catalog
from apps.company import services as company
from apps.media import services as media
from apps.scheduling import availability
from apps.scheduling import serializers as scheduling_serializers
from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_BOOKING
from config.api import ApiError

from . import public
from . import public_serializers as serializers

ERROR = OpenApiResponse(description="Formato de error estándar (`code`, `detail`, `fields`).")


class PublicView(APIView):
    """Sin autenticación ni CSRF (no hay sesión). Solo existe en el host de un negocio; las
    fechas entran y salen en su zona horaria."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    needs_booking_module = True

    def dispatch(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return super().dispatch(request, *args, **kwargs)
        with timezone.override(ZoneInfo(tenant.timezone)):
            return super().dispatch(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if getattr(request, "tenant", None) is None:
            raise ApiError("not_found", "No encontrado.", 404)
        if self.needs_booking_module and not tenancy.is_module_enabled(
            request.tenant, MODULE_BOOKING
        ):
            raise ApiError("module_disabled", "Este negocio no tiene reservas en línea.", 403)


class PublicCompanyView(PublicView):
    needs_booking_module = False  # la página del negocio existe aunque no reciba reservas

    @extend_schema(responses=serializers.PublicCompanySerializer)
    def get(self, request):
        tenant = request.tenant
        info = company.get_company(tenant)
        data = {
            "name": info.trade_name if info else tenant.name,
            "vertical": tenant.vertical,
            "language": tenant.language,
            "timezone": tenant.timezone,
            "currency": tenant.currency,
            "theme": tenant.theme or {},
            "logo": media.media_urls(info.logo) if info else None,
            "booking_enabled": tenancy.is_module_enabled(tenant, MODULE_BOOKING),
            "cancel_min_hours": tenant.cancel_min_hours,
        }
        for field in ("address", "city", "phone", "email", "terms_html", "privacy_html"):
            data[field] = getattr(info, field, "") if info else ""
        data["cookies_html"] = info.cookies_html if info else ""
        data["social_links"] = (info.social_links or {}) if info else {}
        return Response(serializers.PublicCompanySerializer(data).data)


class PublicServicesView(PublicView):
    @extend_schema(responses=serializers.PublicCategorySerializer(many=True))
    def get(self, request):
        categories: OrderedDict = OrderedDict()
        for service in catalog.active_services():
            category = categories.setdefault(
                service.category_id,
                {"id": service.category_id, "name": service.category.name, "services": []},
            )
            category["services"].append(service)
        return Response(
            serializers.PublicCategorySerializer(list(categories.values()), many=True).data
        )


def _service_ids(request) -> list:
    query = scheduling_serializers.AvailabilityQuerySerializer(
        data={"service_ids": request.query_params.getlist("service_ids")}
    )
    query.is_valid(raise_exception=True)
    return query.validated_data["service_ids"]


class PublicProfessionalsView(PublicView):
    @extend_schema(
        parameters=[OpenApiParameter("service_ids", str, many=True, required=True)],
        responses=serializers.PublicProfessionalSerializer(many=True),
    )
    def get(self, request):
        services = availability.resolve_services(_service_ids(request))
        professionals = availability.candidates(services, public=True)
        prefetch_related_objects(professionals, "specialties")  # una consulta, no una por ficha
        return Response(serializers.PublicProfessionalSerializer(professionals, many=True).data)


def _availability_query(request, serializer_class):
    params = request.query_params
    query = serializer_class(data={**params.dict(), "service_ids": params.getlist("service_ids")})
    query.is_valid(raise_exception=True)
    return query.validated_data


AVAILABILITY_PARAMS = [
    OpenApiParameter("service_ids", str, many=True, required=True),
    OpenApiParameter("professional_id", str, description="Vacío = cualquiera"),
]


class PublicSlotsView(PublicView):
    @extend_schema(
        parameters=[*AVAILABILITY_PARAMS, OpenApiParameter("date", str, required=True)],
        responses=scheduling_serializers.SlotSerializer(many=True),
    )
    def get(self, request):
        query = _availability_query(request, scheduling_serializers.SlotsQuerySerializer)
        slots = availability.get_available_slots(
            request.tenant,
            query["service_ids"],
            query["date"],
            query["professional_id"],
            public=True,
        )
        # Con "cualquiera" el cliente no ve quién atiende: se asigna al confirmar (spec §8.7).
        data = scheduling_serializers.SlotSerializer(slots, many=True).data
        if query["professional_id"] is None:
            for slot in data:
                slot["professional_ids"] = []
        return Response(data)


class PublicDaysView(PublicView):
    @extend_schema(
        parameters=[*AVAILABILITY_PARAMS, OpenApiParameter("month", str, required=True)],
        responses=scheduling_serializers.DaysSerializer,
    )
    def get(self, request):
        query = _availability_query(request, scheduling_serializers.DaysQuerySerializer)
        year, month = (int(part) for part in query["month"].split("-"))
        calendar = availability.get_month_calendar(
            request.tenant,
            query["service_ids"],
            year,
            month,
            query["professional_id"],
            public=True,
        )
        return Response(
            scheduling_serializers.DaysSerializer(
                scheduling_serializers.DaysSerializer.build(calendar)
            ).data
        )


def _appointment_data(tenant, appointment) -> dict:
    data = serializers.PublicAppointmentSerializer(
        {
            **{
                field: getattr(appointment, field)
                for field in ("status", "start_at", "end_at", "price_total")
            },
            "professional": appointment.professional,
            "location": appointment.location,
            "customer": appointment.customer,
            "items": appointment.items,
            "can_cancel": public.can_cancel(tenant, appointment),
            "cancel_deadline": public.cancel_deadline(tenant, appointment),
        }
    ).data
    return data


class PublicBookView(PublicView):
    @extend_schema(
        request=serializers.PublicBookingSerializer,
        responses={
            201: serializers.PublicBookedSerializer,
            409: OpenApiResponse(description="`slot_taken` con horarios sugeridos."),
            429: OpenApiResponse(description="`rate_limited`: 10 por hora por IP, 5 por celular."),
            400: ERROR,
        },
    )
    def post(self, request):
        data = serializers.PublicBookingSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appointment = public.by_token(
            public.book(request.tenant, request, data.validated_data).cancel_token
        )
        body = _appointment_data(request.tenant, appointment)
        body["manage_url"] = request.build_absolute_uri(f"/cita/{appointment.cancel_token}")
        return Response(body, status=status.HTTP_201_CREATED)


class PublicAppointmentView(PublicView):
    @extend_schema(responses={200: serializers.PublicAppointmentSerializer, 404: ERROR})
    def get(self, request, token):
        return Response(_appointment_data(request.tenant, public.by_token(token)))


class PublicCancelView(PublicView):
    @extend_schema(
        request=serializers.PublicCancelSerializer,
        responses={
            200: serializers.PublicAppointmentSerializer,
            409: OpenApiResponse(description="`cancel_window_closed` o `invalid_transition`."),
        },
    )
    def post(self, request, token):
        data = serializers.PublicCancelSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appointment = public.cancel(request.tenant, token, reason=data.validated_data["reason"])
        return Response(
            _appointment_data(request.tenant, public.by_token(appointment.cancel_token))
        )
