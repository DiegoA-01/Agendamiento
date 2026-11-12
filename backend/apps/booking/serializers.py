from rest_framework import serializers

from .models import Appointment


class CustomerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField()


class AppointmentItemSerializer(serializers.Serializer):
    service_id = serializers.UUIDField()
    price_charged = serializers.DecimalField(max_digits=12, decimal_places=2)
    duration_min = serializers.IntegerField()


class AppointmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=Appointment.Status.choices)
    source = serializers.ChoiceField(choices=Appointment.Source.choices)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    professional_id = serializers.UUIDField()
    resource_id = serializers.UUIDField(allow_null=True)
    location_id = serializers.UUIDField()
    customer = CustomerSerializer()
    attendee_name = serializers.CharField(help_text="Para quién es, si no es para el cliente.")
    items = AppointmentItemSerializer(many=True, source="items.all")
    price_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    cancelled_at = serializers.DateTimeField(allow_null=True)
    cancel_reason = serializers.CharField()
    rescheduled_from_id = serializers.UUIDField(allow_null=True)
    created_at = serializers.DateTimeField()


class NewCustomerSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    marketing_consent = serializers.BooleanField(required=False, default=False)


class AppointmentCreateSerializer(serializers.Serializer):
    """`professional_id` vacío = cualquiera. El cliente va por `customer_id` o por `customer`
    (se busca por celular y se crea si no existe). Fechas sin zona = hora del negocio."""

    service_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=10)
    professional_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    start_at = serializers.DateTimeField()
    customer_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    customer = NewCustomerSerializer(required=False, allow_null=True, default=None)
    attendee_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        if (attrs["customer_id"] is None) == (attrs["customer"] is None):
            raise serializers.ValidationError(
                {"customer": ["Indica customer_id o los datos del cliente, no ambos."]}
            )
        return attrs


class AppointmentUpdateSerializer(serializers.Serializer):
    resource_id = serializers.UUIDField(required=False, allow_null=True)


class AppointmentFilterSerializer(serializers.Serializer):
    start_at = serializers.DateTimeField(required=False)
    end_at = serializers.DateTimeField(required=False)
    professional_id = serializers.UUIDField(required=False)
    customer_id = serializers.UUIDField(required=False)
    status = serializers.MultipleChoiceField(choices=Appointment.Status.choices, required=False)


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=250, required=False, allow_blank=True, default="")


class RescheduleSerializer(serializers.Serializer):
    start_at = serializers.DateTimeField()
    professional_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class SlotTakenFieldsSerializer(serializers.Serializer):
    suggestions = serializers.ListField(child=serializers.DateTimeField())


class SlotTakenSerializer(serializers.Serializer):
    """Respuesta 409 `slot_taken`: el horario ya no está libre; trae horarios sugeridos."""

    code = serializers.CharField()
    detail = serializers.CharField()
    fields = SlotTakenFieldsSerializer()


class CustomerDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    phone = serializers.CharField(help_text="E.164, p. ej. +573001234567")
    email = serializers.EmailField(allow_blank=True)
    birthday = serializers.DateField(allow_null=True)
    notes = serializers.CharField(allow_blank=True)
    marketing_consent = serializers.BooleanField()
    data_consent_at = serializers.DateTimeField()
    appointments_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class CustomerWriteSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30)
    email = serializers.EmailField(required=False, allow_blank=True)
    birthday = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    marketing_consent = serializers.BooleanField(required=False)


class CustomerCreateSerializer(CustomerWriteSerializer):
    data_consent = serializers.BooleanField(
        write_only=True,
        help_text="Confirma que el cliente autorizó el tratamiento de sus datos (Ley 1581).",
    )

    def validate_data_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                "El cliente debe autorizar el tratamiento de sus datos."
            )
        return value
