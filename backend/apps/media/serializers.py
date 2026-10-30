from rest_framework import serializers

from . import services
from .models import MediaFile


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class MediaUrlsSerializer(serializers.Serializer):
    thumb = serializers.CharField()
    medium = serializers.CharField()
    large = serializers.CharField()


class MediaFileSerializer(serializers.ModelSerializer):
    urls = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = ["id", "original_name", "width", "height", "urls"]

    def get_urls(self, media: MediaFile) -> MediaUrlsSerializer:
        return services.media_urls(media)  # type: ignore[return-value]
