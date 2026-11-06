import binascii
import hmac

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from .models import BankStatement, Transaction
from .throttles import clear_failed_logins, record_failed_login

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )


class RateLimitedTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        request = self.context.get('request')
        username = attrs.get('username', '')

        try:
            token_pair = super().validate(attrs)
        except AuthenticationFailed:
            record_failed_login(request, username)
            raise

        try:
            validate_password(attrs.get('password', ''), user=self.user)
        except DjangoValidationError:
            clear_failed_logins(request, username)
            raise AuthenticationFailed(
                'Your password does not meet the current security requirements. '
                'Request a password reset to continue.',
                code='password_reset_required',
            )

        clear_failed_logins(request, username)
        return token_pair


class PasswordRevokingTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            refresh = self.token_class(attrs['refresh'])
            user_id = refresh.payload.get(jwt_api_settings.USER_ID_CLAIM)
            user = User.objects.get(pk=user_id, is_active=True)
        except (TokenError, User.DoesNotExist, TypeError, ValueError) as error:
            raise InvalidToken('Token is invalid or expired.') from error

        token_password_hash = refresh.payload.get(
            jwt_api_settings.REVOKE_TOKEN_CLAIM, ''
        )
        current_password_hash = get_md5_hash_password(user.password)
        if not hmac.compare_digest(token_password_hash, current_password_hash):
            raise InvalidToken('Token is invalid or expired.')

        return super().validate(attrs)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        invalid_link = serializers.ValidationError({
            'token': ['This password reset link is invalid or expired.']
        })

        try:
            user_id = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=user_id, is_active=True)
        except (
            User.DoesNotExist,
            TypeError,
            ValueError,
            OverflowError,
            UnicodeDecodeError,
            binascii.Error,
        ):
            raise invalid_link

        if not default_token_generator.check_token(user, attrs['token']):
            raise invalid_link

        try:
            validate_password(attrs['new_password'], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'new_password': error.messages})

        attrs['user'] = user
        return attrs

class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'date', 'payee_payer', 'description', 'amount', 'transaction_type', 'category']

class BankStatementSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = BankStatement
        fields = ['id', 'file', 'uploaded_at', 'is_processed', 'ai_evaluation', 'transactions']
        read_only_fields = ['is_processed', 'uploaded_at', 'ai_evaluation']