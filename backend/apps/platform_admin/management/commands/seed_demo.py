"""Negocio de demostración para desarrollo y pruebas de extremo a extremo (spec §16).

    python manage.py seed_demo --vertical barbershop
    python manage.py seed_demo --vertical salon --slug salon-demo --password Clave-Demo-2026!

Crea el negocio con su subdominio, la empresa y su sede, un propietario, 3 profesionales,
6 servicios del vertical, horario de lunes a sábado de 9:00 a 19:00 y citas de
muestra en los próximos días hábiles. Todo pasa por los `services.py` de cada app, igual que la
API: así el negocio demo cumple las mismas reglas que uno real.
"""

import datetime as dt
import secrets
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts import services as accounts
from apps.booking import services as booking
from apps.catalog import services as catalog
from apps.company import services as company
from apps.scheduling import services as scheduling
from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_KEYS
from apps.tenancy.context import tenant_context
from config.api import ApiError

PLAN_NAME = "Demo"
# (categoría, servicio, minutos, precio en COP)
SERVICES = {
    "barbershop": [
        ("Cortes", "Corte clásico", 30, "30000"),
        ("Cortes", "Corte con diseño", 45, "40000"),
        ("Cortes", "Corte infantil", 30, "25000"),
        ("Barba", "Perfilado de barba", 20, "18000"),
        ("Barba", "Barba con toalla caliente", 30, "25000"),
        ("Barba", "Corte y barba", 60, "50000"),
    ],
    "salon": [
        ("Cabello", "Corte de dama", 45, "45000"),
        ("Cabello", "Cepillado", 40, "35000"),
        ("Cabello", "Tinte completo", 120, "150000"),
        ("Cabello", "Mechas", 150, "220000"),
        ("Tratamientos", "Hidratación profunda", 45, "60000"),
        ("Tratamientos", "Keratina", 180, "250000"),
    ],
    "nails": [
        ("Manos", "Manicure tradicional", 40, "25000"),
        ("Manos", "Manicure semipermanente", 60, "45000"),
        ("Manos", "Uñas acrílicas", 120, "90000"),
        ("Pies", "Pedicure tradicional", 50, "30000"),
        ("Pies", "Pedicure spa", 70, "50000"),
        ("Pies", "Pedicure semipermanente", 70, "55000"),
    ],
}
PROFESSIONALS = [
    ("Andrés", Decimal("40")),
    ("Camila", Decimal("45")),
    ("Julián", Decimal("40")),
]
CUSTOMERS = [
    ("Laura Gómez", "3001112233"),
    ("Mateo Rojas", "3104445566"),
    ("Sofía Herrera", "3157778899"),
]
WORKING_DAYS = range(0, 6)  # lunes a sábado
OPEN, CLOSE = dt.time(9, 0), dt.time(19, 0)
SAMPLE_HOURS = (10, 15)  # citas de muestra a las 10:00 y a las 15:00


# Tema de muestra: verde oscuro y dorado, como la referencia de diseño de la reserva (R9). Pasa la
# validación de contraste (texto 13.5:1 sobre el fondo y 10.6:1 sobre las superficies).
DEMO_THEMES = {
    "barbershop": {
        "primary": "#d4ae63",
        "secondary": "#d4ae63",
        "background": "#0e2620",
        "surface": "#163a2f",
        "text": "#f3ecdc",
    },
}


class Command(BaseCommand):
    help = "Crea un negocio de demostración con equipo, servicios, horarios y citas de muestra."

    def add_arguments(self, parser):
        parser.add_argument("--vertical", choices=sorted(SERVICES), default="barbershop")
        parser.add_argument("--slug", default="", help="Subdominio (por defecto demo-<vertical>).")
        parser.add_argument(
            "--password",
            default="",
            help="Contraseña del propietario. Si no se indica, se genera y se muestra una vez.",
        )

    def handle(self, *args, vertical: str, slug: str, password: str, **options):
        slug = slug or f"demo-{vertical}"
        if tenancy.get_tenant_by_slug(slug) is not None:
            raise CommandError(f"Ya existe un negocio con el subdominio '{slug}'. Usa --slug.")
        password = password or secrets.token_urlsafe(12)

        try:
            with transaction.atomic():
                tenant, owner_email = self._create_business(vertical, slug, password)
                with tenant_context(tenant):
                    professionals = self._create_team(tenant, vertical)
                    booked = self._book_samples(tenant, professionals)
        except ApiError as exc:
            raise CommandError(f"No se pudo crear el negocio demo: {exc.detail}") from exc

        self.stdout.write(self.style.SUCCESS(f"Negocio demo '{tenant.name}' creado."))
        self.stdout.write(f"  Dirección:   http://{tenancy.subdomain_host(slug)}")
        self.stdout.write(f"  Propietario: {owner_email}")
        self.stdout.write(f"  Contraseña:  {password}")
        self.stdout.write(
            f"  {len(professionals)} profesionales, {len(SERVICES[vertical])} servicios, "
            f"{booked} citas de muestra."
        )

    def _create_business(self, vertical: str, slug: str, password: str):
        plan = tenancy.list_plans().filter(name=PLAN_NAME).first() or tenancy.create_plan(
            name=PLAN_NAME, modules=list(MODULE_KEYS), max_professionals=10, max_locations=1
        )
        names = {"barbershop": "Barbería", "salon": "Salón", "nails": "Uñas"}
        tenant = tenancy.create_tenant(
            name=f"{names[vertical]} Demo", slug=slug, plan=plan, vertical=vertical
        )
        if vertical in DEMO_THEMES:
            tenancy.set_theme(tenant, DEMO_THEMES[vertical])
        company.create_company(tenant)
        owner_email = f"propietario@{slug}.test"
        accounts.create_tenant_user(
            tenant=tenant,
            email=owner_email,
            full_name="Propietario Demo",
            role="owner",
            password=password,
        )
        return tenant, owner_email

    def _create_team(self, tenant, vertical: str):
        categories: dict[str, Any] = {}
        services = []
        for category_name, name, minutes, price in SERVICES[vertical]:
            if category_name not in categories:
                categories[category_name] = catalog.create_category(
                    name=category_name, sort_order=len(categories)
                )
            services.append(
                catalog.create_service(
                    category_id=categories[category_name].pk,
                    name=name,
                    duration_min=minutes,
                    price=Decimal(price),
                )
            )

        week = [{"weekday": day, "start_time": OPEN, "end_time": CLOSE} for day in WORKING_DAYS]
        professionals = []
        for index, (name, commission) in enumerate(PROFESSIONALS):
            professional = catalog.create_professional(
                tenant, display_name=name, default_commission_pct=commission
            )
            # El último no hace los servicios largos: así "cualquiera" no siempre da los 3.
            offered = services if index < 2 else services[:4]
            catalog.replace_offered_services(
                professional, [{"service_id": service.pk} for service in offered]
            )
            scheduling.replace_working_hours(professional, week)
            professionals.append(professional)
        return professionals

    def _book_samples(self, tenant, professionals) -> int:
        tz = ZoneInfo(tenant.timezone)
        customers = [
            booking.get_or_create_customer(full_name=name, phone=phone) for name, phone in CUSTOMERS
        ]
        days: list[dt.date] = []
        day = timezone.localdate(timezone=tz)
        while len(days) < 3:
            day += dt.timedelta(days=1)
            if day.weekday() in WORKING_DAYS:
                days.append(day)

        booked = 0
        for day_index, day in enumerate(days):
            for slot_index, hour in enumerate(SAMPLE_HOURS):
                professional = professionals[(day_index + slot_index) % len(professionals)]
                service = catalog.list_offered_services(professional).first()
                if service is None:
                    continue
                try:
                    booking.create_appointment(
                        tenant,
                        service_ids=[service.service_id],
                        professional_id=professional.pk,
                        start_at=dt.datetime.combine(day, dt.time(hour), tzinfo=tz),
                        customer=customers[(day_index + slot_index) % len(customers)],
                    )
                    booked += 1
                except ApiError:
                    continue  # el hueco no está libre: la demo sigue sin esa cita
        return booked
