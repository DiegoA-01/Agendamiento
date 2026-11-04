from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path(
        "categories/<uuid:category_id>/",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path("services/", views.ServiceListView.as_view(), name="service-list"),
    path("services/<uuid:service_id>/", views.ServiceDetailView.as_view(), name="service-detail"),
    path("resources/", views.ResourceListView.as_view(), name="resource-list"),
    path(
        "resources/<uuid:resource_id>/",
        views.ResourceDetailView.as_view(),
        name="resource-detail",
    ),
    path("specialties/", views.SpecialtyListView.as_view(), name="specialty-list"),
    path(
        "specialties/<uuid:specialty_id>/",
        views.SpecialtyDetailView.as_view(),
        name="specialty-detail",
    ),
    path("professionals/", views.ProfessionalListView.as_view(), name="professional-list"),
    path(
        "professionals/<uuid:professional_id>/",
        views.ProfessionalDetailView.as_view(),
        name="professional-detail",
    ),
    path(
        "professionals/<uuid:professional_id>/services/",
        views.ProfessionalServicesView.as_view(),
        name="professional-services",
    ),
]
