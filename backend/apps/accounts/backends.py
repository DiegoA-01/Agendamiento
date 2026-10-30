from django.contrib.auth.backends import ModelBackend

from .models import User


class AccountsBackend(ModelBackend):
    """Solo se usa para recuperar al usuario de la sesión (`get_user`); el login lo hace
    `services.login`, que sabe en qué tenant se está entrando."""

    def authenticate(self, request, **credentials):
        return None

    def get_user(self, user_id):
        # Un usuario borrado (lógico) pierde su sesión aunque la cookie siga viva.
        user = User.objects.filter(pk=user_id, deleted_at__isnull=True).first()
        return user if user is not None and self.user_can_authenticate(user) else None


BACKEND_PATH = "apps.accounts.backends.AccountsBackend"
