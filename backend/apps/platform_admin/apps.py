from django.apps import AppConfig


class PlatformAdminConfig(AppConfig):
    name = "apps.platform_admin"
    label = "platform_admin"

    def ready(self) -> None:
        from . import receivers  # noqa: F401 (conecta la auditoría de seguridad)
