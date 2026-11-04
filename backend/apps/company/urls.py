from django.urls import path

from . import views

urlpatterns = [
    path("company/", views.CompanyView.as_view(), name="company"),
    path("locations/", views.LocationListView.as_view(), name="location-list"),
    path(
        "locations/<uuid:location_id>/",
        views.LocationDetailView.as_view(),
        name="location-detail",
    ),
]
