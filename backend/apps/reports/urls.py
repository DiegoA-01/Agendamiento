from django.urls import path

from . import views

urlpatterns = [
    path("reports/sales/", views.SalesReportView.as_view(), name="report-sales"),
    path("reports/sales/export/", views.SalesExportView.as_view(), name="report-sales-export"),
    path("reports/bookings/", views.BookingsReportView.as_view(), name="report-bookings"),
    path(
        "reports/bookings/export/",
        views.BookingsExportView.as_view(),
        name="report-bookings-export",
    ),
]
