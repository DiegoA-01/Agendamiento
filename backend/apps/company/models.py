from django.db import models

from apps.tenancy.models import TenantOwnedModel


class Company(TenantOwnedModel):
    """Datos de la empresa (1:1 con el tenant). El logo llega con la app `media` (M4)."""

    legal_name = models.CharField(max_length=200, blank=True)
    trade_name = models.CharField(max_length=200)
    tax_id = models.CharField(max_length=30, blank=True)  # NIT
    address = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
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
