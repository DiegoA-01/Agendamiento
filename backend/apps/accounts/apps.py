import logging

from django.apps import AppConfig
from django.conf import settings


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"

    def ready(self) -> None:
        from . import schema  # noqa: F401  (registra las extensiones de OpenAPI)

        if not settings.REQUIRE_TWO_FACTOR:
            logging.getLogger(__name__).warning(
                "Verificación en dos pasos DESACTIVADA (REQUIRE_TWO_FACTOR=0). "
                "Solo para pruebas: hay que reactivarla antes de entregar."
            )
