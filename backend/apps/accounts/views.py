from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import serializers, services
from .authentication import CsrfEnforcedSessionAuth


class CsrfView(APIView):
    """Entrega la cookie `csrftoken`; el frontend la lee y la manda en el header X-CSRFToken."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(responses={204: None})
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class _AuthPostView(APIView):
    authentication_classes = [CsrfEnforcedSessionAuth]
    permission_classes = [AllowAny]


class LoginView(_AuthPostView):
    @extend_schema(request=serializers.LoginSerializer, responses=serializers.MeSerializer)
    def post(self, request):
        data = serializers.LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.login(
            request._request,
            data.validated_data["email"],
            data.validated_data["password"],
            data.validated_data["totp_code"],
        )
        return Response(services.build_me(request._request, user))


class LogoutView(APIView):
    authentication_classes = [CsrfEnforcedSessionAuth]
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        services.logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TwoFactorSetupView(_AuthPostView):
    @extend_schema(
        request=serializers.TwoFactorSetupSerializer,
        responses=serializers.TwoFactorSetupResponseSerializer,
    )
    def post(self, request):
        data = serializers.TwoFactorSetupSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result = services.begin_two_factor_setup(
            request._request, data.validated_data["email"], data.validated_data["password"]
        )
        return Response(result)


class TwoFactorConfirmView(_AuthPostView):
    @extend_schema(
        request=serializers.TwoFactorConfirmSerializer, responses=serializers.MeSerializer
    )
    def post(self, request):
        data = serializers.TwoFactorConfirmSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.confirm_two_factor(
            request._request,
            data.validated_data["email"],
            data.validated_data["password"],
            data.validated_data["code"],
        )
        return Response(services.build_me(request._request, user))


class PasswordResetView(_AuthPostView):
    @extend_schema(request=serializers.PasswordResetRequestSerializer, responses={204: None})
    def post(self, request):
        data = serializers.PasswordResetRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.request_password_reset(request._request, data.validated_data["email"])
        # Siempre 204: no revela si el correo existe.
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetConfirmView(_AuthPostView):
    @extend_schema(request=serializers.PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request):
        data = serializers.PasswordResetConfirmSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.confirm_password_reset(
            request._request,
            data.validated_data["uid"],
            data.validated_data["token"],
            data.validated_data["new_password"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    @extend_schema(responses=serializers.MeSerializer)
    def get(self, request):
        return Response(services.build_me(request._request, request.user))
