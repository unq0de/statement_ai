from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import UserSecuritySettings


class SecurityVersionJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        security_settings = UserSecuritySettings.objects.filter(user=user).only(
            'auth_version'
        ).first()
        current_version = security_settings.auth_version if security_settings else 0
        try:
            token_version = int(validated_token.get('auth_version', 0))
        except (TypeError, ValueError) as error:
            raise AuthenticationFailed(
                'Token is invalid or expired.', code='token_not_valid'
            ) from error

        if token_version != current_version:
            raise AuthenticationFailed(
                'Token is invalid or expired.', code='token_not_valid'
            )
        return user
