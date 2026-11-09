from django.urls import path

from . import views

urlpatterns = [
    path("commissions/", views.CommissionListView.as_view(), name="commission-list"),
    path("commissions/export/", views.CommissionExportView.as_view(), name="commission-export"),
    path(
        "commissions/<uuid:entry_id>/adjustments/",
        views.CommissionAdjustmentView.as_view(),
        name="commission-adjust",
    ),
]
