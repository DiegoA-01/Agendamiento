import uuid

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenancy import services as tenancy
from apps.tenancy.constants import MODULE_KEYS
from config.api import ApiError

from . import serializers
from . import services as platform
from .permissions import platform_permissions


class NewestFirstPagination(CursorPagination):
    """Paginación por cursor (spec §9): no se desordena si entran registros mientras se pagina."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"


def _paginate(view, request, queryset, serializer_class):
    paginator = NewestFirstPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)
    return paginator.get_paginated_response(serializer_class(page, many=True).data)


def _tenant_or_404(tenant_id):
    tenant = tenancy.get_tenant(tenant_id)
    if tenant is None:
        raise platform.not_found("Negocio")
    return tenant


def _plan_or_400(plan_id):
    plan = tenancy.get_plan(plan_id)
    if plan is None:
        raise ApiError("validation_error", "Plan inexistente.", 400, {"plan_id": ["No existe."]})
    return plan


class PlatformView(APIView):
    """Base de la API del Super Admin: solo Super Admin y solo en el host `admin.`."""

    def get_permissions(self):
        return platform_permissions(getattr(self.request, "method", "GET"))


# --- Negocios ----------------------------------------------------------------------------------


class TenantListCreateView(PlatformView):
    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="Busca por nombre o subdominio"),
            OpenApiParameter("status", str, enum=["active", "suspended"]),
        ],
        responses=serializers.TenantSerializer(many=True),
    )
    def get(self, request):
        tenants = tenancy.list_tenants(
            search=request.query_params.get("q", "").strip(),
            status=request.query_params.get("status", ""),
        )
        return _paginate(self, request, tenants, serializers.TenantSerializer)

    @extend_schema(
        request=serializers.TenantCreateSerializer,
        responses={201: serializers.TenantCreatedSerializer},
    )
    def post(self, request):
        data = serializers.TenantCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        plan = _plan_or_400(values.pop("plan_id"))
        tenant, owner, password = platform.create_tenant_with_owner(request, plan=plan, **values)
        body = {
            "tenant": serializers.TenantDetailSerializer(tenant).data,
            "owner": {"email": owner.email, "full_name": owner.full_name},
            "temporary_password": password,
        }
        return Response(body, status=status.HTTP_201_CREATED)


class TenantDetailView(PlatformView):
    @extend_schema(responses=serializers.TenantDetailSerializer)
    def get(self, request, tenant_id):
        return Response(serializers.TenantDetailSerializer(_tenant_or_404(tenant_id)).data)

    @extend_schema(
        request=serializers.TenantUpdateSerializer, responses=serializers.TenantDetailSerializer
    )
    def patch(self, request, tenant_id):
        tenant = _tenant_or_404(tenant_id)
        data = serializers.TenantUpdateSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        changes = dict(data.validated_data)
        if "plan_id" in changes:
            changes["plan"] = _plan_or_400(changes.pop("plan_id"))
        tenant = platform.update_tenant(request, tenant, **changes)
        return Response(serializers.TenantDetailSerializer(tenant).data)

    @extend_schema(responses={204: None})
    def delete(self, request, tenant_id):
        platform.delete_tenant(request, _tenant_or_404(tenant_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class TenantStatusView(PlatformView):
    suspend = False

    @extend_schema(request=None, responses=serializers.TenantDetailSerializer)
    def post(self, request, tenant_id):
        tenant = platform.set_status(request, _tenant_or_404(tenant_id), suspend=self.suspend)
        return Response(serializers.TenantDetailSerializer(tenant).data)


class TenantThemeView(PlatformView):
    @extend_schema(responses=serializers.ThemeSerializer)
    def get(self, request, tenant_id):
        return Response(_tenant_or_404(tenant_id).theme)

    @extend_schema(request=serializers.ThemeSerializer, responses=serializers.ThemeSerializer)
    def put(self, request, tenant_id):
        tenant = _tenant_or_404(tenant_id)
        return Response(platform.set_theme(request, tenant, request.data))


def _modules_payload(tenant) -> dict:
    return {"available": list(MODULE_KEYS), "enabled": sorted(tenancy.enabled_module_keys(tenant))}


class TenantModulesView(PlatformView):
    @extend_schema(responses=serializers.ModulesSerializer)
    def get(self, request, tenant_id):
        return Response(_modules_payload(_tenant_or_404(tenant_id)))

    @extend_schema(
        request=serializers.ModulesWriteSerializer, responses=serializers.ModulesSerializer
    )
    def put(self, request, tenant_id):
        tenant = _tenant_or_404(tenant_id)
        data = serializers.ModulesWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        platform.set_modules(request, tenant, data.validated_data["modules"])
        return Response(_modules_payload(tenant))


# --- Dominios ----------------------------------------------------------------------------------


def _domain_or_404(tenant, domain_id):
    domain = tenancy.get_domain(tenant, domain_id)
    if domain is None:
        raise platform.not_found("Dominio")
    return domain


class TenantDomainsView(PlatformView):
    @extend_schema(responses=serializers.DomainSerializer(many=True))
    def get(self, request, tenant_id):
        tenant = _tenant_or_404(tenant_id)
        domains = tenancy.list_domains(tenant)
        return Response(serializers.DomainSerializer(domains, many=True).data)

    @extend_schema(
        request=serializers.DomainCreateSerializer, responses={201: serializers.DomainSerializer}
    )
    def post(self, request, tenant_id):
        tenant = _tenant_or_404(tenant_id)
        data = serializers.DomainCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        domain = platform.add_domain(request, tenant, data.validated_data["host"])
        return Response(serializers.DomainSerializer(domain).data, status=status.HTTP_201_CREATED)


class TenantDomainDetailView(PlatformView):
    @extend_schema(responses={204: None})
    def delete(self, request, tenant_id, domain_id):
        tenant = _tenant_or_404(tenant_id)
        platform.remove_domain(request, tenant, _domain_or_404(tenant, domain_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class TenantDomainVerifyView(PlatformView):
    @extend_schema(request=None, responses=serializers.DomainVerificationSerializer)
    def post(self, request, tenant_id, domain_id):
        tenant = _tenant_or_404(tenant_id)
        result = platform.verify_domain(request, tenant, _domain_or_404(tenant, domain_id))
        return Response(result)


# --- Planes ------------------------------------------------------------------------------------


def _plan_or_404(plan_id):
    plan = tenancy.get_plan(plan_id)
    if plan is None:
        raise platform.not_found("Plan")
    return plan


class PlanListCreateView(PlatformView):
    @extend_schema(responses=serializers.PlanSerializer(many=True))
    def get(self, request):
        return Response(serializers.PlanSerializer(tenancy.list_plans(), many=True).data)

    @extend_schema(
        request=serializers.PlanWriteSerializer, responses={201: serializers.PlanSerializer}
    )
    def post(self, request):
        data = serializers.PlanWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        plan = platform.create_plan(request, **data.validated_data)
        return Response(serializers.PlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class PlanDetailView(PlatformView):
    @extend_schema(responses=serializers.PlanSerializer)
    def get(self, request, plan_id):
        return Response(serializers.PlanSerializer(_plan_or_404(plan_id)).data)

    @extend_schema(request=serializers.PlanUpdateSerializer, responses=serializers.PlanSerializer)
    def patch(self, request, plan_id):
        plan = _plan_or_404(plan_id)
        data = serializers.PlanUpdateSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        apply = values.pop("apply_to_tenants", False)
        plan = platform.update_plan(request, plan, apply_to_tenants=apply, **values)
        return Response(serializers.PlanSerializer(plan).data)

    @extend_schema(responses={204: None})
    def delete(self, request, plan_id):
        platform.delete_plan(request, _plan_or_404(plan_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Auditoría ---------------------------------------------------------------------------------


class AuditLogView(PlatformView):
    @extend_schema(
        parameters=[
            OpenApiParameter("tenant_id", str, description="Solo acciones sobre ese negocio"),
            OpenApiParameter("action", str, description="Ej.: tenant.suspend"),
        ],
        responses=serializers.AuditLogSerializer(many=True),
    )
    def get(self, request):
        raw_tenant_id = request.query_params.get("tenant_id")
        try:
            tenant_id = uuid.UUID(raw_tenant_id) if raw_tenant_id else None
        except ValueError as exc:
            raise ApiError(
                "validation_error", "Filtro inválido.", 400, {"tenant_id": ["UUID inválido."]}
            ) from exc
        logs = platform.list_audit_log(
            tenant_id=tenant_id, action=request.query_params.get("action", "")
        )
        return _paginate(self, request, logs, serializers.AuditLogSerializer)
