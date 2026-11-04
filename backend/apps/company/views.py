from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import permissions as perms

from . import serializers
from . import services as company


class IsTenantUser(BasePermission):
    """Sesión iniciada en el host de un negocio (no en `admin.`)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(request, "tenant", None))


class CompanyResourceView(APIView):
    """Datos de la empresa y sedes (matriz §5, recurso `company`): el propietario edita y el
    administrador solo ve. Los demás roles reciben 403."""

    def get_permissions(self):
        action = "view" if self.request.method == "GET" else "update"
        return [IsTenantUser(), perms.permission_for(perms.COMPANY, action)()]


class CompanyView(CompanyResourceView):
    @extend_schema(responses=serializers.CompanySerializer)
    def get(self, request):
        return Response(serializers.CompanySerializer(company.current_company()).data)

    @extend_schema(
        request=serializers.CompanyUpdateSerializer, responses=serializers.CompanySerializer
    )
    def patch(self, request):
        data = serializers.CompanyUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        updated = company.update_company(company.current_company(), **data.validated_data)
        return Response(serializers.CompanySerializer(updated).data)


class LocationListView(CompanyResourceView):
    @extend_schema(responses=serializers.LocationSerializer(many=True))
    def get(self, request):
        return Response(serializers.LocationSerializer(company.list_locations(), many=True).data)

    @extend_schema(
        request=serializers.LocationSerializer,
        responses={201: serializers.LocationSerializer},
    )
    def post(self, request):
        data = serializers.LocationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        location = company.create_location(request.tenant, **data.validated_data)
        return Response(
            serializers.LocationSerializer(location).data, status=status.HTTP_201_CREATED
        )


class LocationDetailView(CompanyResourceView):
    @extend_schema(responses=serializers.LocationSerializer)
    def get(self, request, location_id):
        return Response(serializers.LocationSerializer(company.get_location(location_id)).data)

    @extend_schema(
        request=serializers.LocationSerializer(partial=True),
        responses=serializers.LocationSerializer,
    )
    def patch(self, request, location_id):
        location = company.get_location(location_id)
        data = serializers.LocationSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        updated = company.update_location(location, **data.validated_data)
        return Response(serializers.LocationSerializer(updated).data)

    @extend_schema(responses={204: None})
    def delete(self, request, location_id):
        company.delete_location(company.get_location(location_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
