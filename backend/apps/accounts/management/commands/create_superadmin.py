from getpass import getpass

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Crea un usuario Super Admin (sin tenant). Pide la contraseña por consola."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", default="Super Admin")
        parser.add_argument(
            "--password",
            help="Solo para scripts y tests: en la consola queda en el historial. Mejor omitirlo.",
        )

    def handle(self, *args, **options) -> None:
        email, name = options["email"], options["name"]
        password = options["password"]
        if not password:
            password = getpass("Contraseña: ")
            if password != getpass("Repite la contraseña: "):
                raise CommandError("Las contraseñas no coinciden.")
        try:
            validate_password(password, User(email=email, full_name=name))
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        try:
            User.objects.create_superadmin(email, password, full_name=name)
        except IntegrityError as exc:
            raise CommandError(f"Ya existe un Super Admin con el correo {email}.") from exc
        note = (
            "En su primer login deberá activar el 2FA."
            if settings.REQUIRE_TWO_FACTOR
            else "El 2FA está desactivado aquí (REQUIRE_TWO_FACTOR=0): entra solo con contraseña."
        )
        self.stdout.write(self.style.SUCCESS(f"Super Admin creado: {email}. {note}"))
