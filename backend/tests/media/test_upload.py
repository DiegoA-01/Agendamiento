import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.media import services as media
from apps.media.models import MediaFile
from apps.tenancy.context import tenant_context
from config.api import ApiError
from tests.accounts.factories import UserFactory
from tests.accounts.helpers import ADMIN_HOST, host, login
from tests.media.factories import MediaFileFactory
from tests.tenancy.factories import TenantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def image_file(fmt="PNG", size=(2400, 1200), mode="RGB", name="foto.png", **save_kwargs):
    buffer = io.BytesIO()
    Image.new(mode, size, (200, 30, 30) if mode == "RGB" else (200, 30, 30, 128)).save(
        buffer, format=fmt, **save_kwargs
    )
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


def open_variant(media_file: MediaFile, field: str) -> Image.Image:
    with getattr(media_file, field).open("rb") as handle:
        image = Image.open(io.BytesIO(handle.read()))
        image.load()
        return image


@pytest.fixture
def tenant():
    tenant = TenantFactory()
    with tenant_context(tenant):
        yield tenant


# --- Servicio -----------------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_every_variant_is_webp_with_its_max_side(tenant, fmt):
    uploaded = media.upload_image(image_file(fmt, name=f"foto.{fmt.lower()}"))

    assert (uploaded.width, uploaded.height) == (2400, 1200)
    for field, max_side in media.VARIANTS.items():
        variant = open_variant(uploaded, field)
        assert variant.format == "WEBP"
        assert variant.size == (max_side, max_side // 2)
        assert getattr(uploaded, field).name.endswith(f"{field}.webp")


def test_small_images_are_never_enlarged(tenant):
    uploaded = media.upload_image(image_file(size=(300, 150)))
    assert open_variant(uploaded, "thumb").size == (200, 100)
    assert open_variant(uploaded, "medium").size == (300, 150)
    assert open_variant(uploaded, "large").size == (300, 150)


def test_transparency_is_kept(tenant):
    uploaded = media.upload_image(image_file(mode="RGBA", size=(400, 400)))
    assert open_variant(uploaded, "medium").mode == "RGBA"


def test_camera_rotation_is_applied_and_exif_is_dropped(tenant):
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: girar 90°
    exif[0x010F] = "CámaraSecreta"  # Make: no debe sobrevivir a la conversión
    uploaded = media.upload_image(
        image_file("JPEG", size=(400, 200), name="foto.jpg", exif=exif.tobytes())
    )

    assert (uploaded.width, uploaded.height) == (200, 400)
    variant = open_variant(uploaded, "medium")
    assert variant.size == (200, 400)
    assert not variant.getexif()


@pytest.mark.parametrize(
    "upload, code",
    [
        (SimpleUploadedFile("nota.png", b"no soy una imagen"), "invalid_image"),
        (image_file("GIF", name="animado.gif"), "unsupported_image"),
        (image_file("BMP", name="viejo.bmp"), "unsupported_image"),
    ],
)
def test_rejects_files_that_are_not_allowed_images(tenant, upload, code):
    with pytest.raises(ApiError) as error:
        media.upload_image(upload)
    assert error.value.code == code
    assert not MediaFile.objects.exists()


def test_rejects_files_over_the_size_limit(tenant, settings):
    settings.MEDIA_MAX_UPLOAD_BYTES = 1000
    with pytest.raises(ApiError) as error:
        media.upload_image(image_file())
    assert error.value.code == "file_too_large"


def test_rejects_images_with_too_many_pixels(tenant, monkeypatch):
    monkeypatch.setattr(media, "MAX_PIXELS", 100 * 100)
    with pytest.raises(ApiError) as error:
        media.upload_image(image_file(size=(101, 100)))
    assert error.value.code == "image_too_large"


def test_get_media_only_finds_images_of_the_active_tenant(tenant):
    own = MediaFileFactory()
    with tenant_context(TenantFactory()):
        other = MediaFileFactory()

    assert media.get_media(own.pk) == own
    assert media.get_media(other.pk) is None
    assert media.get_media("no-es-un-uuid") is None


# --- API ----------------------------------------------------------------------------------------


def upload(client, at, file=None):
    return client.post("/api/v1/media/", {"file": file or image_file()}, HTTP_HOST=at)


@pytest.mark.parametrize("role", ["owner", "admin"])
def test_owner_and_admin_can_upload(role):
    user = UserFactory(role=role)
    client = APIClient()
    login(client, user, host(user.tenant.slug))

    response = upload(client, host(user.tenant.slug))

    assert response.status_code == 201, response.json()
    body = response.json()
    assert (body["width"], body["height"]) == (2400, 1200)
    assert body["original_name"] == "foto.png"
    assert set(body["urls"]) == {"thumb", "medium", "large"}
    assert body["urls"]["thumb"].startswith(f"/media/tenants/{user.tenant_id}/{body['id']}/")
    with tenant_context(user.tenant):
        assert MediaFile.objects.filter(pk=body["id"]).exists()


@pytest.mark.parametrize("role", ["receptionist", "professional"])
def test_other_roles_cannot_upload(role):
    user = UserFactory(role=role)
    client = APIClient()
    login(client, user, host(user.tenant.slug))
    assert upload(client, host(user.tenant.slug)).status_code == 403


def test_anonymous_cannot_upload():
    tenant = TenantFactory()
    assert upload(APIClient(), host(tenant.slug)).status_code == 401


def test_an_invalid_file_returns_the_standard_error_format():
    user = UserFactory(role="owner")
    client = APIClient()
    login(client, user, host(user.tenant.slug))

    response = upload(client, host(user.tenant.slug), SimpleUploadedFile("x.png", b"basura"))

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_image"
    assert "file" in response.json()["fields"]


def test_the_platform_host_has_no_media_upload(settings):
    assert upload(APIClient(), ADMIN_HOST).status_code in (401, 403)


def test_webp_files_are_served_with_their_image_type():
    import mimetypes

    assert mimetypes.guess_type("thumb.webp")[0] == "image/webp"
