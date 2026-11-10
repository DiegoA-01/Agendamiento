from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "apps.notifications"
    label = "notifications"

    def ready(self) -> None:
        from . import receivers  # noqa: F401  (escucha los cambios de cita)
