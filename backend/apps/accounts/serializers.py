from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    totp_code = serializers.CharField(required=False, allow_blank=True, default="")


class TwoFactorSetupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TwoFactorConfirmSerializer(TwoFactorSetupSerializer):
    code = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


# Solo documentan la respuesta en OpenAPI.
class UserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    phone = serializers.CharField()


class MeTenantSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    vertical = serializers.CharField()
    timezone = serializers.CharField()
    currency = serializers.CharField()
    language = serializers.CharField()


class MeSerializer(serializers.Serializer):
    user = UserSummarySerializer()
    role = serializers.CharField()
    two_factor_enabled = serializers.BooleanField()
    is_platform_admin = serializers.BooleanField()
    tenant = MeTenantSerializer(allow_null=True)
    theme = serializers.DictField()
    modules = serializers.ListField(child=serializers.CharField())


class TwoFactorSetupResponseSerializer(serializers.Serializer):
    secret = serializers.CharField()
    otpauth_uri = serializers.CharField()
