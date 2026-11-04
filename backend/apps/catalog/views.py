from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import permissions as perms

from . import serializers
from . import services as catalog

ACTION_BY_METHOD = {"GET": "view", "POST": "create", "PATCH": "update", "DELETE": "delete"}


class IsTenantUser(BasePermission):
    """Sesión iniciada en el host de un negocio (no en `admin.`)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(request, "tenant", None))


class CatalogView(APIView):
    """Catálogo del negocio (matriz §5, recurso `staff_services`): propietario y administrador
    hacen CRUD, recepción ve todo y el profesional ve solo lo propio."""

    def get_permissions(self):
        action = ACTION_BY_METHOD.get(self.request.method or "GET", "view")
        return [IsTenantUser(), perms.permission_for(perms.STAFF_SERVICES, action)()]


def _validated(serializer_class, data, *, partial=False) -> dict:
    serializer = serializer_class(data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# --- Categorías ---------------------------------------------------------------------------------


class CategoryListView(CatalogView):
    @extend_schema(responses=serializers.CategorySerializer(many=True))
    def get(self, request):
        categories = catalog.list_categories(request.user)
        return Response(serializers.CategorySerializer(categories, many=True).data)

    @extend_schema(
        request=serializers.CategorySerializer, responses={201: serializers.CategorySerializer}
    )
    def post(self, request):
        category = catalog.create_category(
            **_validated(serializers.CategorySerializer, request.data)
        )
        return Response(
            serializers.CategorySerializer(category).data, status=status.HTTP_201_CREATED
        )


class CategoryDetailView(CatalogView):
    @extend_schema(responses=serializers.CategorySerializer)
    def get(self, request, category_id):
        category = catalog.get_category(request.user, category_id)
        return Response(serializers.CategorySerializer(category).data)

    @extend_schema(
        request=serializers.CategorySerializer(partial=True),
        responses=serializers.CategorySerializer,
    )
    def patch(self, request, category_id):
        category = catalog.get_category(request.user, category_id)
        changes = _validated(serializers.CategorySerializer, request.data, partial=True)
        updated = catalog.update_category(category, **changes)
        return Response(serializers.CategorySerializer(updated).data)

    @extend_schema(responses={204: None})
    def delete(self, request, category_id):
        catalog.delete_category(catalog.get_category(request.user, category_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Servicios ----------------------------------------------------------------------------------


class ServiceListView(CatalogView):
    @extend_schema(
        parameters=[
            OpenApiParameter("category_id", str, description="Filtra por categoría"),
            OpenApiParameter("is_active", bool, description="Filtra activos o inactivos"),
        ],
        responses=serializers.ServiceSerializer(many=True),
    )
    def get(self, request):
        is_active = request.query_params.get("is_active")
        category_id = request.query_params.get("category_id")
        services = catalog.list_services(
            request.user,
            category_id=category_id or None,
            is_active=None if is_active is None else is_active.lower() in ("1", "true"),
        )
        return Response(serializers.ServiceSerializer(services, many=True).data)

    @extend_schema(
        request=serializers.ServiceSerializer, responses={201: serializers.ServiceSerializer}
    )
    def post(self, request):
        service = catalog.create_service(**_validated(serializers.ServiceSerializer, request.data))
        return Response(serializers.ServiceSerializer(service).data, status=status.HTTP_201_CREATED)


class ServiceDetailView(CatalogView):
    @extend_schema(responses=serializers.ServiceSerializer)
    def get(self, request, service_id):
        service = catalog.get_service(request.user, service_id)
        return Response(serializers.ServiceSerializer(service).data)

    @extend_schema(
        request=serializers.ServiceSerializer(partial=True),
        responses=serializers.ServiceSerializer,
    )
    def patch(self, request, service_id):
        service = catalog.get_service(request.user, service_id)
        changes = _validated(serializers.ServiceSerializer, request.data, partial=True)
        updated = catalog.update_service(service, **changes)
        return Response(serializers.ServiceSerializer(updated).data)

    @extend_schema(responses={204: None})
    def delete(self, request, service_id):
        catalog.delete_service(catalog.get_service(request.user, service_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Puestos ------------------------------------------------------------------------------------


class ResourceListView(CatalogView):
    @extend_schema(responses=serializers.ResourceSerializer(many=True))
    def get(self, request):
        resources = catalog.list_resources(request.user)
        return Response(serializers.ResourceSerializer(resources, many=True).data)

    @extend_schema(
        request=serializers.ResourceSerializer, responses={201: serializers.ResourceSerializer}
    )
    def post(self, request):
        data = _validated(serializers.ResourceSerializer, request.data)
        resource = catalog.create_resource(request.tenant, **data)
        return Response(
            serializers.ResourceSerializer(resource).data, status=status.HTTP_201_CREATED
        )


class ResourceDetailView(CatalogView):
    @extend_schema(responses=serializers.ResourceSerializer)
    def get(self, request, resource_id):
        resource = catalog.get_resource_for(request.user, resource_id)
        return Response(serializers.ResourceSerializer(resource).data)

    @extend_schema(
        request=serializers.ResourceSerializer(partial=True),
        responses=serializers.ResourceSerializer,
    )
    def patch(self, request, resource_id):
        resource = catalog.get_resource_for(request.user, resource_id)
        changes = _validated(serializers.ResourceSerializer, request.data, partial=True)
        updated = catalog.update_resource(request.tenant, resource, **changes)
        return Response(serializers.ResourceSerializer(updated).data)

    @extend_schema(responses={204: None})
    def delete(self, request, resource_id):
        catalog.delete_resource(catalog.get_resource_for(request.user, resource_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
