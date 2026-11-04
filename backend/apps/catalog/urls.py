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
]
