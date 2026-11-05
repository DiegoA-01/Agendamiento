from django.urls import path

from . import public_views, views

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

# Reserva pública (M6): sin sesión, el negocio sale del host.
urlpatterns += [
    path("public/company/", public_views.PublicCompanyView.as_view(), name="public-company"),
    path("public/services/", public_views.PublicServicesView.as_view(), name="public-services"),
    path(
        "public/professionals/",
        public_views.PublicProfessionalsView.as_view(),
        name="public-professionals",
    ),
    path(
        "public/availability/days/",
        public_views.PublicDaysView.as_view(),
        name="public-availability-days",
    ),
    path(
        "public/availability/slots/",
        public_views.PublicSlotsView.as_view(),
        name="public-availability-slots",
    ),
    path("public/appointments/", public_views.PublicBookView.as_view(), name="public-book"),
    path(
        "public/appointments/<str:token>/",
        public_views.PublicAppointmentView.as_view(),
        name="public-appointment",
    ),
    path(
        "public/appointments/<str:token>/cancel/",
        public_views.PublicCancelView.as_view(),
        name="public-cancel",
    ),
]
