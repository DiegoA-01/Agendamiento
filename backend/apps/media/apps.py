import mimetypes

from django.apps import AppConfig


class MediaConfig(AppConfig):
    name = "apps.media"
    label = "media"

    def ready(self) -> None:
        # La imagen de Docker no trae el tipo de WebP: sin esto se sirve como octet-stream.
        mimetypes.add_type("image/webp", ".webp")
