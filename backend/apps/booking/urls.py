from django.urls import path

from . import views

ITEM = "appointments/<uuid:appointment_id>/"

urlpatterns = [
    path("appointments/", views.AppointmentListCreateView.as_view(), name="appointment-list"),
    path(ITEM, views.AppointmentDetailView.as_view(), name="appointment-detail"),
    path(f"{ITEM}confirm/", views.ConfirmView.as_view(), name="appointment-confirm"),
    path(f"{ITEM}start/", views.StartView.as_view(), name="appointment-start"),
    path(f"{ITEM}complete/", views.CompleteView.as_view(), name="appointment-complete"),
    path(f"{ITEM}cancel/", views.CancelView.as_view(), name="appointment-cancel"),
    path(f"{ITEM}no-show/", views.NoShowView.as_view(), name="appointment-no-show"),
    path(f"{ITEM}reschedule/", views.RescheduleView.as_view(), name="appointment-reschedule"),
]
