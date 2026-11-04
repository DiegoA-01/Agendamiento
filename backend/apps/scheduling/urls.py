from django.urls import path

from .views import (
    AgendaSettingsView,
    AvailabilityDaysView,
    AvailabilitySlotsView,
    TimeBlockDetailView,
    TimeBlockListCreateView,
    WorkingHoursView,
)

urlpatterns = [
    path("availability/slots/", AvailabilitySlotsView.as_view(), name="availability-slots"),
    path("availability/days/", AvailabilityDaysView.as_view(), name="availability-days"),
    path("agenda-settings/", AgendaSettingsView.as_view(), name="agenda-settings"),
    path(
        "professionals/<uuid:professional_id>/working-hours/",
        WorkingHoursView.as_view(),
        name="working-hours",
    ),
    path("time-blocks/", TimeBlockListCreateView.as_view(), name="time-block-list"),
    path("time-blocks/<uuid:block_id>/", TimeBlockDetailView.as_view(), name="time-block-detail"),
]
