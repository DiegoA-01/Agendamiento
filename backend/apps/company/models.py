from django.db import models
from django.db.models import Q

from apps.tenancy.models import TenantOwnedModel


class Company(TenantOwnedModel):
    """Datos de la empresa (1:1 con el tenant)."""

    legal_name = models.CharField(max_length=200, blank=True)
    trade_name = models.CharField(max_length=200)
    tax_id = models.CharField(max_length=30, blank=True)  # NIT
    address = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ForeignKey(
        "media.MediaFile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    terms_html = models.TextField(blank=True)
    privacy_html = models.TextField(blank=True)
    cookies_html = models.TextField(blank=True)
    social_links = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "companies"
        constraints = [
            models.UniqueConstraint(fields=["tenant"], name="uniq_company_per_tenant"),
        ]

    def __str__(self) -> str:
        return self.trade_name


class Location(TenantOwnedModel):
    """Sede. El MVP usa una sola (la de `is_default`), pero el modelo ya admite varias."""

    name = models.CharField(max_length=150)
    address = models.CharField(max_length=250, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                condition=Q(is_default=True, deleted_at__isnull=True),
                name="uniq_default_location_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return self.name
