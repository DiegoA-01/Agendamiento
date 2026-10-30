from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.tenancy.models import BaseModel


class UserManager(BaseUserManager["User"]):
    def for_tenant(self, tenant) -> models.QuerySet["User"]:
        """Usuarios vigentes de un tenant; `tenant=None` = usuarios de plataforma (Super Admin).

        Toda consulta de usuarios para login o reset pasa por aquí: nunca mezcla tenants.
        """
        queryset = self.filter(deleted_at__isnull=True)
        return (
            queryset.filter(tenant=tenant)
            if tenant is not None
            else queryset.filter(tenant__isnull=True)
        )

    def create_user(self, email: str, password: str, *, role: str, tenant=None, **extra) -> "User":
        user = self.model(email=email, role=role, tenant=tenant, **extra)
        user.set_password(password)
        user.save()
        return user

    def create_superadmin(self, email: str, password: str, **extra) -> "User":
        return self.create_user(email, password, role=User.Role.SUPERADMIN, tenant=None, **extra)


class User(BaseModel, AbstractBaseUser):
    """Persona que entra al sistema. Es modelo de identidad (como Tenant o Domain), no de negocio:
    no hereda de `TenantOwnedModel` porque el Super Admin no tiene tenant. Por eso todas las
    consultas pasan por `User.objects.for_tenant(...)`."""

    class Role(models.TextChoices):
        SUPERADMIN = "superadmin"
        OWNER = "owner"
        ADMIN = "admin"
        RECEPTIONIST = "receptionist"
        PROFESSIONAL = "professional"

    email = models.EmailField()
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True, on_delete=models.PROTECT, related_name="users"
    )
    is_active = models.BooleanField(default=True)
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_enabled = models.BooleanField(default=False)
    totp_last_step = models.BigIntegerField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        constraints = [
            # Mismo correo en dos negocios distintos sí; dos veces en el mismo negocio no.
            models.UniqueConstraint(
                Lower("email"),
                "tenant",
                name="uniq_user_email_per_tenant",
                condition=Q(tenant__isnull=False),
            ),
            # Entre Super Admins el correo es único global.
            models.UniqueConstraint(
                Lower("email"),
                name="uniq_superadmin_email",
                condition=Q(tenant__isnull=True),
            ),
            # Solo el superadmin carece de tenant, y todo lo demás debe tener uno.
            models.CheckConstraint(
                name="user_role_tenant_consistent",
                condition=Q(role="superadmin", tenant__isnull=True)
                | (~Q(role="superadmin") & Q(tenant__isnull=False)),
            ),
        ]

    def __str__(self) -> str:
        return self.email

    def clean(self) -> None:
        if (self.role == self.Role.SUPERADMIN) != (self.tenant_id is None):
            raise ValidationError("Solo el superadmin carece de tenant.")

    def save(self, *args, **kwargs) -> None:
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
