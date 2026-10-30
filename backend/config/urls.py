from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from .health import healthz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]
