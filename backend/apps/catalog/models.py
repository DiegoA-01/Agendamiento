from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.tenancy.models import TenantOwnedModel

MONEY = {"max_digits": 12, "decimal_places": 2}
PERCENT = {"max_digits": 5, "decimal_places": 2}


class ServiceCategory(TenantOwnedModel):
    name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "service categories"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class Service(TenantOwnedModel):
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    duration_min = models.PositiveIntegerField()
    buffer_min = models.PositiveIntegerField(default=0)
    price = models.DecimalField(**MONEY)
    is_active = models.BooleanField(default=True)
    requires_resource = models.BooleanField(default=False)
    image = models.ForeignKey(
        "media.MediaFile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Reservado para anticipos (Wompi, fuera del MVP): sin uso.
    deposit_required = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(duration_min__gt=0), name="service_duration_gt_0"),
            models.CheckConstraint(condition=Q(price__gte=0), name="service_price_gte_0"),
        ]

    def __str__(self) -> str:
        return self.name


class Specialty(TenantOwnedModel):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "specialties"

    def __str__(self) -> str:
        return self.name


class Professional(TenantOwnedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    location = models.ForeignKey(
        "company.Location", on_delete=models.PROTECT, related_name="professionals"
    )
    display_name = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    photo = models.ForeignKey(
        "media.MediaFile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Tabla intermedia propia para que también tenga tenant y RLS. Al usar `.add()` hay que pasar
    # `through_defaults={"tenant": tenant}` (el alta masiva no pasa por `save()`).
    specialties = models.ManyToManyField(
        Specialty, through="ProfessionalSpecialty", blank=True, related_name="professionals"
    )
    default_commission_pct = models.DecimalField(**PERCENT, default=0)
    is_active = models.BooleanField(default=True)
    accepts_online_booking = models.BooleanField(default=True)
    # Reservado para reseñas (fuera del MVP): sin uso.
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(default_commission_pct__gte=0, default_commission_pct__lte=100),
                name="professional_commission_pct_range",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(user__isnull=False, deleted_at__isnull=True),
                name="uniq_professional_per_user",
            ),
        ]

    def __str__(self) -> str:
        return self.display_name


class ProfessionalSpecialty(TenantOwnedModel):
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name="+")
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, related_name="+")

    class Meta:
        verbose_name_plural = "professional specialties"
        constraints = [
            models.UniqueConstraint(
                fields=["professional", "specialty"], name="uniq_professional_specialty"
            ),
        ]


class ProfessionalService(TenantOwnedModel):
    """Servicio que ofrece un profesional, con precio, comisión y duración opcionales propios."""

    professional = models.ForeignKey(
        Professional, on_delete=models.CASCADE, related_name="service_links"
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="professional_links"
    )
    price_override = models.DecimalField(**MONEY, null=True, blank=True)
    commission_pct_override = models.DecimalField(**PERCENT, null=True, blank=True)
    duration_override_min = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["professional", "service"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_professional_service",
            ),
            models.CheckConstraint(
                condition=Q(commission_pct_override__isnull=True)
                | Q(commission_pct_override__gte=0, commission_pct_override__lte=100),
                name="professional_service_commission_pct_range",
            ),
            models.CheckConstraint(
                condition=Q(duration_override_min__isnull=True) | Q(duration_override_min__gt=0),
                name="professional_service_duration_gt_0",
            ),
            models.CheckConstraint(
                condition=Q(price_override__isnull=True) | Q(price_override__gte=0),
                name="professional_service_price_gte_0",
            ),
        ]


class Resource(TenantOwnedModel):
    """Puesto de trabajo (silla, camilla...). `Service.requires_resource` exige uno libre."""

    location = models.ForeignKey(
        "company.Location", on_delete=models.PROTECT, related_name="resources"
    )
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name
