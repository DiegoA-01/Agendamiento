"""API pública de la app media: subida de imágenes convertidas a WebP (spec §2).

Otras apps guardan una FK a `MediaFile` y usan `get_media` para validar el id que llega del
cliente (debe ser del tenant activo) y `media_urls` para serializar.
"""

import io
import uuid
import warnings
from typing import IO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.tenancy.context import get_current_tenant
from config.api import ApiError

from .models import MediaFile

# Lado mayor de cada variante, en píxeles. Nunca se agranda una imagen más pequeña.
VARIANTS = {"thumb": 200, "medium": 800, "large": 1600}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
WEBP_QUALITY = 82
# Más píxeles que esto se rechaza: protege contra "bombas" de descompresión (archivos pequeños
# que al abrirse ocupan gigas de memoria). 40 MP cubre las fotos de cualquier celular actual.
MAX_PIXELS = 40_000_000


def _invalid(code: str, detail: str) -> ApiError:
    return ApiError(code, detail, 400, {"file": [detail]})


def _open_image(upload: IO[bytes]) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(upload)
            if image.format not in ALLOWED_FORMATS:
                raise _invalid("unsupported_image", "Formato no permitido. Usa JPG, PNG o WebP.")
            if image.width * image.height > MAX_PIXELS:
                raise _invalid("image_too_large", "La imagen tiene demasiados píxeles.")
            image.load()  # decodifica ya: un archivo corrupto falla aquí y no al guardar
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise _invalid("image_too_large", "La imagen tiene demasiados píxeles.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise _invalid("invalid_image", "El archivo no es una imagen válida.") from exc
    return image


def _normalize(image: Image.Image) -> Image.Image:
    """Aplica la rotación de la cámara (EXIF) y deja la imagen en RGB o RGBA.

    Volver a codificar descarta el EXIF, que puede traer la ubicación GPS de la foto.
    """
    image = ImageOps.exif_transpose(image) or image
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    return image.convert("RGBA" if has_alpha else "RGB")


def _to_webp(image: Image.Image, max_side: int) -> bytes:
    variant = image.copy()
    variant.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    variant.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=4)
    return buffer.getvalue()


def upload_image(upload: IO[bytes], *, original_name: str = "") -> MediaFile:
    """Valida, convierte a WebP en tres tamaños y guarda. Corre dentro del tenant activo."""
    size = getattr(upload, "size", None)
    if size is not None and size > settings.MEDIA_MAX_UPLOAD_BYTES:
        limit_mb = settings.MEDIA_MAX_UPLOAD_BYTES // (1024 * 1024)
        raise _invalid("file_too_large", f"La imagen pesa más de {limit_mb} MB.")

    tenant = get_current_tenant()
    if tenant is None:
        raise ApiError("no_tenant", "No hay negocio activo.", 400)

    image = _normalize(_open_image(upload))
    # El tenant va desde ya (y no al guardar): la ruta de los archivos lo incluye.
    media = MediaFile(
        id=uuid.uuid4(),
        tenant=tenant,
        original_name=original_name[:255],
        width=image.width,
        height=image.height,
    )
    for field, max_side in VARIANTS.items():
        getattr(media, field).save(
            f"{field}.webp", ContentFile(_to_webp(image, max_side)), save=False
        )
    media.save()
    return media


def get_media(media_id) -> MediaFile | None:
    """Imagen vigente del tenant activo, o None (también si el id es de otro tenant)."""
    try:
        return MediaFile.objects.filter(pk=media_id).first()
    except (ValidationError, ValueError, TypeError):
        return None


def media_urls(media: MediaFile | None) -> dict[str, str] | None:
    if media is None:
        return None
    return {field: getattr(media, field).url for field in VARIANTS if getattr(media, field)}
