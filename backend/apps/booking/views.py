from zoneinfo import ZoneInfo

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_BOOKING
from config.api import ApiError

from . import serializers
from . import services as booking


class IsTenantUser(BasePermission):
    """Sesión iniciada en el host de un negocio. El rol y el alcance se revisan en `services`."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(request, "tenant", None))


class BookingView(APIView):
    """Base de las citas del panel: exige el módulo `booking` del plan y usa la zona horaria del
    negocio (una fecha sin zona se interpreta en hora local y la respuesta lleva el desfase)."""

    permission_classes = [IsTenantUser]

    def dispatch(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return super().dispatch(request, *args, **kwargs)
        with timezone.override(ZoneInfo(tenant.timezone)):
            return super().dispatch(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)  # autenticación y permisos primero
        if not tenancy.is_module_enabled(request.tenant, MODULE_BOOKING):
            raise ApiError("module_disabled", "El módulo 'booking' no está habilitado.", 403)


class ByStartPagination(CursorPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    ordering = ("start_at", "id")


SLOT_TAKEN = OpenApiResponse(
    serializers.SlotTakenSerializer, description="El horario ya no está libre (`slot_taken`)."
)
INVALID_TRANSITION = OpenApiResponse(
    description="Transición de estado no válida (`invalid_transition`, spec §7)."
)


def _data(appointment):
    return serializers.AppointmentSerializer(appointment).data


class AppointmentListCreateView(BookingView):
    @extend_schema(
        parameters=[
            OpenApiParameter("start_at", str, description="Citas que terminan después de"),
            OpenApiParameter("end_at", str, description="Citas que empiezan antes de"),
            OpenApiParameter("professional_id", str),
            OpenApiParameter("customer_id", str),
            OpenApiParameter("status", str, many=True),
        ],
        responses=serializers.AppointmentSerializer(many=True),
    )
    def get(self, request):
        params = request.query_params
        filters = serializers.AppointmentFilterSerializer(
            data={**params.dict(), "status": params.getlist("status")}
            if "status" in params
            else params
        )
        filters.is_valid(raise_exception=True)
        appointments = booking.list_appointments(request.user, **filters.validated_data)
        paginator = ByStartPagination()
        page = paginator.paginate_queryset(appointments, request, view=self)
        return paginator.get_paginated_response(
            serializers.AppointmentSerializer(page, many=True).data
        )

    @extend_schema(
        request=serializers.AppointmentCreateSerializer,
        responses={201: serializers.AppointmentSerializer, 409: SLOT_TAKEN},
    )
    def post(self, request):
        booking.require_permission(request.user, "create")
        data = serializers.AppointmentCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        if values["customer_id"] is not None:
            customer = booking.get_customer(values["customer_id"])
        else:
            customer = booking.get_or_create_customer(**values["customer"])
        appointment = booking.create_appointment(
            request.tenant,
            service_ids=values["service_ids"],
            start_at=values["start_at"],
            customer=customer,
            professional_id=values["professional_id"],
            created_by=request.user,
        )
        return Response(_data(appointment), status=status.HTTP_201_CREATED)


class AppointmentDetailView(BookingView):
    @extend_schema(responses=serializers.AppointmentSerializer)
    def get(self, request, appointment_id):
        return Response(_data(booking.get_appointment(request.user, appointment_id)))

    @extend_schema(
        request=serializers.AppointmentUpdateSerializer,
        responses={200: serializers.AppointmentSerializer, 409: INVALID_TRANSITION},
    )
    def patch(self, request, appointment_id):
        data = serializers.AppointmentUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appointment = booking.update_appointment(
            request.user, appointment_id, **data.validated_data
        )
        return Response(_data(appointment))


class AppointmentActionView(BookingView):
    """confirm, start, complete y no-show: solo cambian el estado."""

    action_name = ""

    @extend_schema(
        request=None, responses={200: serializers.AppointmentSerializer, 409: INVALID_TRANSITION}
    )
    def post(self, request, appointment_id):
        appointment = booking.change_status(request.user, appointment_id, self.action_name)
        return Response(_data(appointment))


class ConfirmView(AppointmentActionView):
    action_name = "confirm"


class StartView(AppointmentActionView):
    action_name = "start"


class CompleteView(AppointmentActionView):
    action_name = "complete"


class NoShowView(AppointmentActionView):
    action_name = "no_show"


class CancelView(BookingView):
    @extend_schema(
        request=serializers.CancelSerializer,
        responses={200: serializers.AppointmentSerializer, 409: INVALID_TRANSITION},
    )
    def post(self, request, appointment_id):
        data = serializers.CancelSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appointment = booking.change_status(
            request.user, appointment_id, "cancel", reason=data.validated_data["reason"]
        )
        return Response(_data(appointment))


class RescheduleView(BookingView):
    @extend_schema(
        request=serializers.RescheduleSerializer,
        responses={201: serializers.AppointmentSerializer, 409: SLOT_TAKEN},
        description="Crea la cita nueva (enlazada con `rescheduled_from_id`) y deja la original "
        "en `rescheduled`. Si el horario nuevo no está libre, nada cambia.",
    )
    def post(self, request, appointment_id):
        data = serializers.RescheduleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appointment = booking.reschedule(
            request.user, request.tenant, appointment_id, **data.validated_data
        )
        return Response(_data(appointment), status=status.HTTP_201_CREATED)
