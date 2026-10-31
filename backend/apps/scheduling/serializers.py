from rest_framework import serializers


class WorkingHoursSerializer(serializers.Serializer):
    """Franja semanal en hora local del negocio. 0 = lunes ... 6 = domingo."""

    weekday = serializers.IntegerField(min_value=0, max_value=6)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError({"end_time": ["Debe ser posterior al inicio."]})
        return attrs


class TimeBlockSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    professional_id = serializers.UUIDField(allow_null=True)
    resource_id = serializers.UUIDField(allow_null=True)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    reason = serializers.CharField()
    created_at = serializers.DateTimeField()


def _check_range(attrs):
    if attrs["start_at"] >= attrs["end_at"]:
        raise serializers.ValidationError({"end_at": ["Debe ser posterior al inicio."]})
    return attrs


class TimeBlockCreateSerializer(serializers.Serializer):
    """Exactamente uno de `professional_id` o `resource_id`. Fechas sin zona = hora del negocio."""

    professional_id = serializers.UUIDField(required=False, allow_null=True)
    resource_id = serializers.UUIDField(required=False, allow_null=True)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        return _check_range(attrs)


class TimeBlockUpdateSerializer(serializers.Serializer):
    start_at = serializers.DateTimeField(required=False)
    end_at = serializers.DateTimeField(required=False)
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)


class TimeBlockFilterSerializer(serializers.Serializer):
    professional_id = serializers.UUIDField(required=False)
    resource_id = serializers.UUIDField(required=False)
    start_at = serializers.DateTimeField(required=False)
    end_at = serializers.DateTimeField(required=False)


class ConflictingAppointmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    status = serializers.CharField()


class TimeBlockConflictFieldsSerializer(serializers.Serializer):
    appointments = ConflictingAppointmentSerializer(many=True)


class TimeBlockConflictSerializer(serializers.Serializer):
    """Respuesta 409 `time_block_conflict`: las citas que impiden el bloqueo."""

    code = serializers.CharField()
    detail = serializers.CharField()
    fields = TimeBlockConflictFieldsSerializer()
