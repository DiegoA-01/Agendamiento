from django.db import models

from apps.tenancy.models import TenantOwnedModel


class Note(TenantOwnedModel):
    text = models.CharField(max_length=100)

    class Meta:
        app_label = "testapp"
