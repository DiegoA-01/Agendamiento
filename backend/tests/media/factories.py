import factory

from apps.media.models import MediaFile
from tests.tenancy.factories import TenantOwnedFactory


class MediaFileFactory(TenantOwnedFactory):
    class Meta:
        model = MediaFile

    original_name = factory.Sequence(lambda n: f"imagen-{n}.png")
