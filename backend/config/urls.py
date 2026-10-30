from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from .health import healthz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.platform_admin.urls")),
    path("api/v1/", include("apps.company.urls")),
    path("api/v1/", include("apps.media.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.scheduling.urls")),
    path("api/v1/", include("apps.booking.urls")),
    path("api/v1/", include("apps.commissions.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

# En desarrollo Django sirve las imágenes subidas. En producción falta servirlas desde Caddy
# (ver `pormejorar.md`).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
