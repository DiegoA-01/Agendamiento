from rest_framework import serializers

MONEY = {"max_digits": 14, "decimal_places": 2}
RATE = {"max_digits": 5, "decimal_places": 2}


class SalesMetricsSerializer(serializers.Serializer):
    sales = serializers.DecimalField(**MONEY)
    commissions = serializers.DecimalField(**MONEY)
    business = serializers.DecimalField(**MONEY)
    appointments = serializers.IntegerField()
    average_ticket = serializers.DecimalField(**MONEY)


class SalesRowSerializer(SalesMetricsSerializer):
    key = serializers.CharField(
        help_text="Fecha ISO (día, lunes de la semana o día 1 del mes) o id."
    )
    label = serializers.CharField()


class RangeSerializer(serializers.Serializer):
    """`from` y `to` son palabras reservadas en Python: se agregan en `get_fields`."""

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = serializers.DateField()
        fields["to"] = serializers.DateField()
        return fields


class SalesReportSerializer(RangeSerializer):
    group_by = serializers.CharField()
    totals = SalesMetricsSerializer()
    rows = SalesRowSerializer(many=True)


class BookingMetricsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    no_show = serializers.IntegerField()
    web = serializers.IntegerField(help_text="Reservas hechas por el cliente en la web.")
    cancellation_rate = serializers.DecimalField(**RATE, help_text="Porcentaje, 12.50 = 12,5 %.")
    no_show_rate = serializers.DecimalField(**RATE)


class BookingRowSerializer(BookingMetricsSerializer):
    key = serializers.CharField(help_text="Mes YYYY-MM o id del servicio o profesional.")
    label = serializers.CharField()


class BookingsReportSerializer(RangeSerializer):
    totals = BookingMetricsSerializer()
    by_month = BookingRowSerializer(many=True)
    by_professional = BookingRowSerializer(many=True)
    by_service = BookingRowSerializer(many=True)
