from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .permissions import CanUploadMedia
from .serializers import MediaFileSerializer, MediaUploadSerializer


class MediaUploadView(APIView):
    """Sube una imagen (JPG, PNG o WebP). Se guarda como WebP en tres tamaños."""

    permission_classes = [CanUploadMedia]
    parser_classes = [MultiPartParser]

    @extend_schema(request=MediaUploadSerializer, responses={201: MediaFileSerializer})
    def post(self, request):
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        media = services.upload_image(upload, original_name=upload.name or "")
        return Response(MediaFileSerializer(media).data, status=status.HTTP_201_CREATED)
