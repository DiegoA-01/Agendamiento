from django.urls import path

from config.urls import urlpatterns as base_urlpatterns
from tests.testapp import views

urlpatterns = [
    *base_urlpatterns,
    path("test/notes/", views.notes),
    path("test/notes-unfiltered/", views.notes_unfiltered),
    path("test/booking-only/", views.booking_only),
]
