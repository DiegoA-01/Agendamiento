from django.urls import path

from . import views

urlpatterns = [
    path("tenants/", views.TenantListCreateView.as_view(), name="tenants"),
    path("tenants/<uuid:tenant_id>/", views.TenantDetailView.as_view(), name="tenant"),
    path(
        "tenants/<uuid:tenant_id>/suspend/",
        views.TenantStatusView.as_view(suspend=True),
        name="tenant-suspend",
    ),
    path(
        "tenants/<uuid:tenant_id>/activate/",
        views.TenantStatusView.as_view(suspend=False),
        name="tenant-activate",
    ),
    path("tenants/<uuid:tenant_id>/theme/", views.TenantThemeView.as_view(), name="tenant-theme"),
    path(
        "tenants/<uuid:tenant_id>/modules/",
        views.TenantModulesView.as_view(),
        name="tenant-modules",
    ),
    path(
        "tenants/<uuid:tenant_id>/domains/",
        views.TenantDomainsView.as_view(),
        name="tenant-domains",
    ),
    path(
        "tenants/<uuid:tenant_id>/domains/<uuid:domain_id>/",
        views.TenantDomainDetailView.as_view(),
        name="tenant-domain",
    ),
    path(
        "tenants/<uuid:tenant_id>/domains/<uuid:domain_id>/verify/",
        views.TenantDomainVerifyView.as_view(),
        name="tenant-domain-verify",
    ),
    path("plans/", views.PlanListCreateView.as_view(), name="plans"),
    path("plans/<uuid:plan_id>/", views.PlanDetailView.as_view(), name="plan"),
    path("audit-log/", views.AuditLogView.as_view(), name="audit-log"),
]
