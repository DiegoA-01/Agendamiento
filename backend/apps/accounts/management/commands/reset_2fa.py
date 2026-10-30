from django.core.management.base import BaseCommand, CommandError

from apps.accounts import services
from apps.accounts.models import User
from apps.tenancy import services as tenancy


class Command(BaseCommand):
    help = (
        "Quita el 2FA de un usuario que perdió su celular. Solo para emergencias: lo ejecuta "
        "quien tiene acceso al servidor. En su próximo login deberá activarlo de nuevo."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument(
            "--tenant",
            help="Slug del negocio del usuario. Sin esta opción se busca entre los Super Admin.",
        )

    def handle(self, *args, **options) -> None:
        tenant = None
        if options["tenant"]:
            tenant = tenancy.get_tenant_by_slug(options["tenant"])
            if tenant is None:
                raise CommandError(f"No existe el negocio '{options['tenant']}'.")
        email = options["email"].strip().lower()
        user = User.objects.for_tenant(tenant).filter(email=email).first()
        if user is None:
            raise CommandError(f"No existe el usuario {email}.")
        services.reset_two_factor(user)
        self.stdout.write(self.style.SUCCESS(f"2FA quitado para {email}."))
