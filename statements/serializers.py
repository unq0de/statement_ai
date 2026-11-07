import binascii
import hmac

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
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
from .audit import record_audit_event
from .throttles import clear_failed_logins, record_failed_login
from .two_factor import create_login_challenge, get_security_settings

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, allow_blank=False)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_password(self, value):
        attributes = {
            name: self.initial_data.get(name, '')
            for name in ('username', 'email')
        }
        user = User(**{
            name: attribute
            for name, attribute in attributes.items()
            if isinstance(attribute, str)
        })
        validate_password(value, user=user)
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password'],
                is_active=False,
            )
            record_audit_event(
                'auth.registration.created',
                request=self.context.get('request'),
                actor=user,
                target_type='user',
                target_id=user.pk,
            )
        return user


class RegistrationConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        invalid_link = serializers.ValidationError({
            'token': ['This email confirmation link is invalid or expired.']
        })

        try:
            user_id = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=user_id, is_active=False)
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

        attrs['user'] = user
        return attrs


class RateLimitedTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        security_settings = get_security_settings(user)
        token['auth_version'] = security_settings.auth_version
        return token

    def validate(self, attrs):
        request = self.context.get('request')
        username = attrs.get('username', '')

        try:
            token_pair = super().validate(attrs)
        except AuthenticationFailed:
            record_failed_login(request, username)
            record_audit_event(
                'auth.login.failed',
                request=request,
                outcome='failure',
            )
            raise

        try:
            validate_password(attrs.get('password', ''), user=self.user)
        except DjangoValidationError:
            clear_failed_logins(request, username)
            record_audit_event(
                'auth.login.rejected_weak_password',
                request=request,
                actor=self.user,
                target_type='user',
                target_id=self.user.pk,
                outcome='failure',
            )
            raise AuthenticationFailed(
                'Your password does not meet the current security requirements. '
                'Request a password reset to continue.',
                code='password_reset_required',
            )

        clear_failed_logins(request, username)
        security_settings = get_security_settings(self.user)
        if settings.TWO_FACTOR_ENABLED and security_settings.two_factor_enabled:
            challenge = create_login_challenge(
                self.user, security_settings.auth_version
            )
            record_audit_event(
                'auth.login.mfa_required',
                request=request,
                actor=self.user,
                target_type='user',
                target_id=self.user.pk,
            )
            return {
                'mfa_required': True,
                'challenge': challenge,
                'expires_in': settings.TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS,
            }

        record_audit_event(
            'auth.login.succeeded',
            request=request,
            actor=self.user,
            target_type='user',
            target_id=self.user.pk,
        )
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

        security_settings = get_security_settings(user, create=False)
        current_version = security_settings.auth_version if security_settings else 0
        try:
            token_version = int(refresh.payload.get('auth_version', 0))
        except (TypeError, ValueError) as error:
            raise InvalidToken('Token is invalid or expired.') from error
        if token_version != current_version:
            raise InvalidToken('Token is invalid or expired.')

        return super().validate(attrs)


class TwoFactorSetupSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TwoFactorCodeSerializer(serializers.Serializer):
    code = serializers.CharField(write_only=True, min_length=6, max_length=6)


class TwoFactorDisableSerializer(TwoFactorCodeSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TwoFactorLoginSerializer(serializers.Serializer):
    challenge = serializers.CharField(write_only=True, max_length=128)
    code = serializers.CharField(write_only=True, required=False, max_length=16)
    recovery_code = serializers.CharField(
        write_only=True, required=False, max_length=32
    )

    def validate(self, attrs):
        if bool(attrs.get('code')) == bool(attrs.get('recovery_code')):
            raise serializers.ValidationError(
                'Provide exactly one of code or recovery_code.'
            )
        return attrs


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
        fields = [
            'id',
            'file',
            'uploaded_at',
            'processing_status',
            'is_processed',
            'ai_evaluation',
            'transactions',
        ]
        read_only_fields = [
            'processing_status',
            'is_processed',
            'uploaded_at',
            'ai_evaluation',
        ]