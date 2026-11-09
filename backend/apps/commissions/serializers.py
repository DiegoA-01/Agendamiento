import datetime as dt

from django.utils import timezone
from rest_framework import serializers

from .models import CommissionEntry

MONEY = {"max_digits": 12, "decimal_places": 2}
MAX_RANGE_DAYS = 366


class RangeQuerySerializer(serializers.Serializer):
    """`from` y `to` en fecha local del negocio, ambos incluidos. Sin fechas: el mes en curso."""

    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    professional_id = serializers.UUIDField(required=False)
    service_id = serializers.UUIDField(required=False)
    category_id = serializers.UUIDField(required=False)

    @classmethod
    def from_request(cls, request, **extra_fields):
        params = request.query_params
        data = {key: params.get(key) for key in (*cls().fields, *extra_fields) if params.get(key)}
        if params.get("from"):
            data["start"] = params["from"]
        if params.get("to"):
            data["end"] = params["to"]
        return cls(data=data)

    def validate(self, attrs):
        today = timezone.localdate()
        start = attrs.get("start") or today.replace(day=1)
        end = attrs.get("end") or (start.replace(day=28) + dt.timedelta(days=4)).replace(
            day=1
        ) - dt.timedelta(days=1)
        if end < start:
            raise serializers.ValidationError({"to": ["Debe ser igual o posterior a 'from'."]})
        if (end - start).days >= MAX_RANGE_DAYS:
            raise serializers.ValidationError({"to": ["El rango máximo es de un año."]})
        attrs["start"], attrs["end"] = start, end
        return attrs


class CommissionQuerySerializer(RangeQuerySerializer):
    kind = serializers.ChoiceField(choices=CommissionEntry.Kind.choices, required=False)


class CommissionEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=CommissionEntry.Kind.choices)
    appointment_id = serializers.UUIDField()
    appointment_start_at = serializers.DateTimeField()
    professional_id = serializers.UUIDField()
    professional_name = serializers.CharField(source="professional.display_name")
    service_id = serializers.UUIDField()
    service_name = serializers.CharField(source="service.name")
    base_amount = serializers.DecimalField(**MONEY)
    pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = serializers.DecimalField(**MONEY)
    business_amount = serializers.DecimalField(**MONEY)
    adjusts_id = serializers.UUIDField(allow_null=True)
    reason = serializers.CharField()
    created_at = serializers.DateTimeField()


class AdjustmentCreateSerializer(serializers.Serializer):
    """Valores corregidos del servicio; el ajuste guarda la diferencia."""

    base_amount = serializers.DecimalField(**MONEY, min_value=0)
    commission_amount = serializers.DecimalField(**MONEY, min_value=0)
    reason = serializers.CharField(max_length=250)
