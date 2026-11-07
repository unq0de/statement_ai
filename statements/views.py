import logging
import hashlib
import math
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pyotp
from cryptography.fernet import InvalidToken
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import (
    BankStatement,
    Transaction,
    TwoFactorLoginChallenge,
    TwoFactorRecoveryCode,
    UserSecuritySettings,
)
from .audit import record_audit_event
from .email_utils import send_case_email
from .serializers import (
    AccountDeleteSerializer,
    BankStatementSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordRevokingTokenRefreshSerializer,
    TwoFactorCodeSerializer,
    TwoFactorDisableSerializer,
    TwoFactorLoginSerializer,
    TwoFactorSetupSerializer,
    RegistrationConfirmSerializer,
    RateLimitedTokenObtainPairSerializer,
    TransactionSerializer,
    UserRegistrationSerializer,
)
from .tasks import process_statement_task
from .throttles import FailedLoginThrottle
from .two_factor import (
    consume_recovery_code,
    create_login_challenge,
    consume_totp_code,
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_recovery_codes,
    get_security_settings,
    hash_recovery_code,
    issue_token_pair,
)
from .usage import get_current_month_window

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _is_valid_pdf_file(file_obj):
    if file_obj is None:
        return False

    file_name = (file_obj.name or '').lower()
    if not file_name.endswith('.pdf'):
        # Some clients send no extension even for valid PDFs. Fall back to a
        # file-signature check to avoid trusting only the filename.
        pass

    sample = file_obj.read(4096)
    file_obj.seek(0)
    if not sample:
        return False

    if sample.startswith(b'%PDF'):
        return True

    return file_name.endswith('.pdf') and b'%PDF' in sample[:2048]


# ------------------------------------------------------------------
# Views
# ------------------------------------------------------------------


class RegisterView(generics.CreateAPIView):

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        self._send_confirmation_email(user)

    @staticmethod
    def _send_confirmation_email(user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        parts = urlsplit(settings.REGISTRATION_CONFIRMATION_URL)
        fragment = parse_qsl(parts.fragment, keep_blank_values=True)
        fragment.extend((('uid', uid), ('token', token)))
        confirmation_link = urlunsplit(parts._replace(fragment=urlencode(fragment)))
        expiry_minutes = max(1, math.ceil(settings.PASSWORD_RESET_TIMEOUT / 60))

        try:
            delivered = send_case_email(
                template_name='registration_confirmation',
                context={
                    'username': user.get_username(),
                    'confirmation_link': confirmation_link,
                    'expiry_minutes': expiry_minutes,
                },
                recipient=user.email,
            )
            if not delivered:
                logger.error('Registration confirmation email was not delivered for user %s.', user.pk)
        except Exception:
            logger.exception('Registration confirmation email delivery failed for user %s.', user.pk)


class RegistrationConfirmationRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        users = User.objects.filter(
            email__iexact=serializer.validated_data['email'],
            is_active=False,
        )
        user = users.first() if users.count() == 1 else None

        if user is not None:
            RegisterView._send_confirmation_email(user)

        record_audit_event(
            'auth.registration_confirmation.requested',
            request=request,
            target_type='user' if user is not None else '',
            target_id=user.pk if user is not None else '',
            details={'account_match': user is not None},
        )

        return Response(
            {'message': 'If an unconfirmed account uses that email, a confirmation email has been sent.'},
            status=status.HTTP_200_OK,
        )


class RegistrationConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegistrationConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            record_audit_event(
                'auth.registration_confirmation.failed',
                request=request,
                outcome='failure',
            )
            raise
        validated_data = serializer.validated_data

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=validated_data['user'].pk)
            if user.is_active or not default_token_generator.check_token(
                user, validated_data['token']
            ):
                record_audit_event(
                    'auth.registration_confirmation.failed',
                    request=request,
                    actor=user,
                    target_type='user',
                    target_id=user.pk,
                    outcome='failure',
                )
                return Response(
                    {'error': 'This email confirmation link is invalid or expired.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.is_active = True
            user.save(update_fields=['is_active'])
            record_audit_event(
                'auth.registration.confirmed',
                request=request,
                actor=user,
                target_type='user',
                target_id=user.pk,
            )

        return Response(
            {'message': 'Your email address has been confirmed. You can now log in.'},
            status=status.HTTP_200_OK,
        )


class LoginView(TokenObtainPairView):

    serializer_class = RateLimitedTokenObtainPairSerializer
    throttle_classes = [FailedLoginThrottle]


def _two_factor_unavailable_response():
    return Response(
        {'error': 'Two-factor authentication is not available.'},
        status=status.HTTP_404_NOT_FOUND,
    )


class TwoFactorStatusView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not settings.TWO_FACTOR_ENABLED:
            return _two_factor_unavailable_response()

        security_settings = get_security_settings(request.user)
        recovery_codes_remaining = TwoFactorRecoveryCode.objects.filter(
            user=request.user,
            used_at__isnull=True,
        ).count()
        return Response(
            {
                'enabled': security_settings.two_factor_enabled,
                'recovery_codes_remaining': recovery_codes_remaining,
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorSetupView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TwoFactorSetupSerializer

    def post(self, request, *args, **kwargs):
        if not settings.TWO_FACTOR_ENABLED:
            return _two_factor_unavailable_response()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data['password']):
            record_audit_event(
                'auth.two_factor.setup_rejected',
                request=request,
                actor=request.user,
                target_type='user',
                target_id=request.user.pk,
                outcome='failure',
            )
            return Response(
                {'error': 'Password confirmation failed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        security_settings = get_security_settings(request.user)
        if security_settings.two_factor_enabled:
            return Response(
                {'error': 'Two-factor authentication is already enabled.'},
                status=status.HTTP_409_CONFLICT,
            )

        secret = pyotp.random_base32()
        security_settings.encrypted_pending_totp_secret = encrypt_totp_secret(secret)
        security_settings.pending_totp_expires_at = (
            timezone.now()
            + timedelta(seconds=settings.TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS * 2)
        )
        security_settings.save(
            update_fields=[
                'encrypted_pending_totp_secret',
                'pending_totp_expires_at',
                'updated_at',
            ]
        )
        record_audit_event(
            'auth.two_factor.setup_started',
            request=request,
            actor=request.user,
            target_type='user',
            target_id=request.user.pk,
        )
        account_name = request.user.email or request.user.get_username()
        return Response(
            {
                'secret': secret,
                'otpauth_url': pyotp.TOTP(secret).provisioning_uri(
                    name=account_name,
                    issuer_name=settings.TWO_FACTOR_ISSUER,
                ),
                'expires_in': settings.TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS * 2,
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorEnableView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TwoFactorCodeSerializer

    def post(self, request, *args, **kwargs):
        if not settings.TWO_FACTOR_ENABLED:
            return _two_factor_unavailable_response()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            security_settings = UserSecuritySettings.objects.select_for_update().get(
                user=request.user
            )
            if (
                not security_settings.encrypted_pending_totp_secret
                or security_settings.pending_totp_expires_at is None
                or security_settings.pending_totp_expires_at <= timezone.now()
            ):
                return Response(
                    {'error': 'Two-factor setup has expired. Start setup again.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                pending_secret = decrypt_totp_secret(
                    security_settings.encrypted_pending_totp_secret
                )
            except InvalidToken:
                logger.exception('Could not decrypt pending TOTP secret for user %s.', request.user.pk)
                return Response(
                    {'error': 'Two-factor setup is invalid. Start setup again.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not consume_totp_code(
                security_settings, pending_secret, serializer.validated_data['code']
            ):
                record_audit_event(
                    'auth.two_factor.enable_failed',
                    request=request,
                    actor=request.user,
                    target_type='user',
                    target_id=request.user.pk,
                    outcome='failure',
                )
                return Response(
                    {'error': 'The verification code is invalid.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            security_settings.two_factor_enabled = True
            security_settings.encrypted_totp_secret = (
                security_settings.encrypted_pending_totp_secret
            )
            security_settings.encrypted_pending_totp_secret = ''
            security_settings.pending_totp_expires_at = None
            security_settings.auth_version += 1
            security_settings.save()
            recovery_codes = generate_recovery_codes(request.user)
            record_audit_event(
                'auth.two_factor.enabled',
                request=request,
                actor=request.user,
                target_type='user',
                target_id=request.user.pk,
            )

        return Response(
            {
                'message': 'Two-factor authentication is enabled.',
                'recovery_codes': recovery_codes,
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorDisableView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TwoFactorDisableSerializer

    def post(self, request, *args, **kwargs):
        if not settings.TWO_FACTOR_ENABLED:
            return _two_factor_unavailable_response()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data['password']):
            return Response(
                {'error': 'Password confirmation failed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            security_settings = UserSecuritySettings.objects.select_for_update().filter(
                user=request.user,
                two_factor_enabled=True,
            ).first()
            if security_settings is None:
                return Response(
                    {'error': 'Two-factor authentication is not enabled.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                secret = decrypt_totp_secret(security_settings.encrypted_totp_secret)
            except InvalidToken:
                return Response(
                    {'error': 'Two-factor authentication could not be verified.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not consume_totp_code(
                security_settings, secret, serializer.validated_data['code']
            ):
                record_audit_event(
                    'auth.two_factor.disable_failed',
                    request=request,
                    actor=request.user,
                    target_type='user',
                    target_id=request.user.pk,
                    outcome='failure',
                )
                return Response(
                    {'error': 'The verification code is invalid.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            security_settings.two_factor_enabled = False
            security_settings.encrypted_totp_secret = ''
            security_settings.encrypted_pending_totp_secret = ''
            security_settings.pending_totp_expires_at = None
            security_settings.auth_version += 1
            security_settings.save()
            TwoFactorRecoveryCode.objects.filter(user=request.user).delete()
            TwoFactorLoginChallenge.objects.filter(
                user=request.user, consumed_at__isnull=True
            ).update(consumed_at=timezone.now())
            record_audit_event(
                'auth.two_factor.disabled',
                request=request,
                actor=request.user,
                target_type='user',
                target_id=request.user.pk,
            )

        return Response(
            {'message': 'Two-factor authentication is disabled. Please log in again.'},
            status=status.HTTP_200_OK,
        )


class TwoFactorRecoveryCodesView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TwoFactorDisableSerializer

    def post(self, request, *args, **kwargs):
        if not settings.TWO_FACTOR_ENABLED:
            return _two_factor_unavailable_response()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data['password']):
            return Response(
                {'error': 'Password confirmation failed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            security_settings = UserSecuritySettings.objects.select_for_update().filter(
                user=request.user,
                two_factor_enabled=True,
            ).first()
            if security_settings is None:
                return Response(
                    {'error': 'Two-factor authentication is not enabled.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                secret = decrypt_totp_secret(security_settings.encrypted_totp_secret)
            except InvalidToken:
                return Response(
                    {'error': 'Two-factor authentication could not be verified.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not consume_totp_code(
                security_settings, secret, serializer.validated_data['code']
            ):
                return Response(
                    {'error': 'The verification code is invalid.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            recovery_codes = generate_recovery_codes(request.user)
            record_audit_event(
                'auth.two_factor.recovery_codes_regenerated',
                request=request,
                actor=request.user,
                target_type='user',
                target_id=request.user.pk,
            )

        return Response(
            {'recovery_codes': recovery_codes},
            status=status.HTTP_200_OK,
        )


class TwoFactorLoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = TwoFactorLoginSerializer

    def post(self, request, *args, **kwargs):
        if not settings.TWO_FACTOR_ENABLED:
            return _two_factor_unavailable_response()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        challenge_value = serializer.validated_data['challenge']
        challenge_hash = hashlib.sha256(challenge_value.encode()).hexdigest()
        now = timezone.now()

        with transaction.atomic():
            challenge = TwoFactorLoginChallenge.objects.select_for_update().select_related(
                'user'
            ).filter(challenge_hash=challenge_hash).first()
            security_settings = (
                UserSecuritySettings.objects.select_for_update().filter(
                    user=challenge.user
                ).first()
                if challenge is not None
                else None
            )
            valid_challenge = (
                challenge is not None
                and challenge.consumed_at is None
                and challenge.expires_at > now
                and challenge.failed_attempts < settings.TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS
                and challenge.user.is_active
                and security_settings is not None
                and security_settings.two_factor_enabled
                and challenge.auth_version == security_settings.auth_version
            )
            if not valid_challenge:
                record_audit_event(
                    'auth.login.mfa_failed',
                    request=request,
                    outcome='failure',
                )
                return Response(
                    {'error': 'Invalid or expired two-factor challenge.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if serializer.validated_data.get('code'):
                try:
                    secret = decrypt_totp_secret(
                        security_settings.encrypted_totp_secret
                    )
                    valid_code = consume_totp_code(
                        security_settings,
                        secret,
                        serializer.validated_data['code'],
                    )
                except InvalidToken:
                    valid_code = False
            else:
                valid_code = consume_recovery_code(
                    challenge.user,
                    serializer.validated_data['recovery_code'],
                )

            if not valid_code:
                challenge.failed_attempts += 1
                if challenge.failed_attempts >= settings.TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS:
                    challenge.consumed_at = now
                challenge.save(update_fields=['failed_attempts', 'consumed_at'])
                record_audit_event(
                    'auth.login.mfa_failed',
                    request=request,
                    actor=challenge.user,
                    target_type='user',
                    target_id=challenge.user.pk,
                    outcome='failure',
                    details={'failed_attempts': challenge.failed_attempts},
                )
                return Response(
                    {'error': 'Invalid or expired two-factor challenge.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            challenge.consumed_at = now
            challenge.save(update_fields=['consumed_at'])
            token_pair = issue_token_pair(
                challenge.user, security_settings.auth_version
            )
            record_audit_event(
                'auth.login.succeeded',
                request=request,
                actor=challenge.user,
                target_type='user',
                target_id=challenge.user.pk,
                details={'two_factor': True},
            )

        return Response(token_pair, status=status.HTTP_200_OK)


class PasswordRevokingTokenRefreshView(TokenRefreshView):

    serializer_class = PasswordRevokingTokenRefreshSerializer


class PasswordResetRequestView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        users = User.objects.filter(
            email__iexact=email,
            is_active=True,
        )
        user = users.first() if users.count() == 1 else None

        if user is not None:
            self._send_reset_email(user)

        record_audit_event(
            'auth.password_reset.requested',
            request=request,
            target_type='user' if user is not None else '',
            target_id=user.pk if user is not None else '',
            details={'account_match': user is not None},
        )

        return Response(
            {'message': 'If an active account uses that email, reset instructions have been sent.'},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _send_reset_email(user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = settings.PASSWORD_RESET_URL

        if reset_url:
            parts = urlsplit(reset_url)
            fragment = parse_qsl(parts.fragment, keep_blank_values=True)
            fragment.extend((('uid', uid), ('token', token)))
            reset_link = urlunsplit(parts._replace(fragment=urlencode(fragment)))
        else:
            reset_link = ''

        expiry_minutes = max(1, math.ceil(settings.PASSWORD_RESET_TIMEOUT / 60))

        try:
            delivered = send_case_email(
                template_name='password_reset',
                context={
                    'username': user.get_username(),
                    'reset_link': reset_link,
                    'uid': uid,
                    'token': token,
                    'expiry_minutes': expiry_minutes,
                },
                recipient=user.email,
            )
            if not delivered:
                logger.error('Password reset email was not delivered for user %s.', user.pk)
        except Exception:
            logger.exception('Password reset email delivery failed for user %s.', user.pk)


class PasswordResetConfirmView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            record_audit_event(
                'auth.password_reset.failed',
                request=request,
                outcome='failure',
            )
            raise
        validated_data = serializer.validated_data

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=validated_data['user'].pk)
            if not default_token_generator.check_token(user, validated_data['token']):
                record_audit_event(
                    'auth.password_reset.failed',
                    request=request,
                    actor=user,
                    target_type='user',
                    target_id=user.pk,
                    outcome='failure',
                )
                return Response(
                    {'error': 'This password reset link is invalid or expired.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(validated_data['new_password'])
            user.save(update_fields=['password'])
            record_audit_event(
                'auth.password_reset.completed',
                request=request,
                actor=user,
                target_type='user',
                target_id=user.pk,
            )

        return Response(
            {'message': 'Your password has been reset. Please log in again.'},
            status=status.HTTP_200_OK,
        )


class StatementListView(generics.ListAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankStatementSerializer

    def get_queryset(self):
        queryset = BankStatement.objects.filter(user=self.request.user)

        processed_value = self.request.query_params.get('processed')
        if processed_value is not None:
            queryset = queryset.filter(is_processed=processed_value.lower() in {'1', 'true', 'yes', 'on'})

        ordering = self.request.query_params.get('ordering', '-uploaded_at')
        if ordering in {'uploaded_at', '-uploaded_at'}:
            return queryset.order_by(ordering)

        return queryset.order_by('-uploaded_at')


class StatementDetailView(generics.RetrieveDestroyAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankStatementSerializer

    def get_queryset(self):
        return BankStatement.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        record_audit_event(
            'statement.deleted',
            request=self.request,
            actor=self.request.user,
            target_type='statement',
            target_id=instance.pk,
        )
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()

    def delete(self, request, *args, **kwargs):
        super().delete(request, *args, **kwargs)
        return Response(
            {
                "message": "Bank statement and all related transactions were deleted successfully."
            },
            status=status.HTTP_200_OK,
        )


class StatementUploadView(generics.CreateAPIView):

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):

        file_obj = request.FILES.get("file") or request.FILES.get("document")
        if not file_obj:

            return Response(
                {"error": "No file uploaded (field 'file' is required)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = (file_obj.content_type or '').split(';', 1)[0].strip().lower()
        if content_type not in {"application/pdf", "application/octet-stream", "binary/octet-stream"}:
            return Response(
                {"error": "Only PDF files are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not _is_valid_pdf_file(file_obj):
            return Response(
                {"error": "Uploaded file is not a valid PDF."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file_obj.size > MAX_UPLOAD_SIZE_BYTES:
            return Response(
                {"error": "File too large (max. 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement = None
        try:
            with transaction.atomic():
                if settings.GEMINI_MONTHLY_LIMIT_PER_USER:
                    user = User.objects.select_for_update().get(pk=request.user.pk)
                    month_start, next_month = get_current_month_window()
                    monthly_usage = BankStatement.objects.filter(
                        user=user,
                        uploaded_at__gte=month_start,
                        uploaded_at__lt=next_month,
                    ).count()
                    if monthly_usage >= settings.GEMINI_MONTHLY_LIMIT_PER_USER:
                        retry_after = max(
                            1,
                            math.ceil((next_month - timezone.localtime()).total_seconds()),
                        )
                        record_audit_event(
                            'statement.upload.limit_reached',
                            request=request,
                            actor=user,
                            outcome='failure',
                            details={
                                'limit': settings.GEMINI_MONTHLY_LIMIT_PER_USER,
                                'used': monthly_usage,
                            },
                        )
                        return Response(
                            {
                                'error': 'Monthly statement processing limit reached.',
                                'limit': settings.GEMINI_MONTHLY_LIMIT_PER_USER,
                                'used': monthly_usage,
                            },
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                            headers={'Retry-After': str(retry_after)},
                        )

                statement = BankStatement.objects.create(
                    user=request.user, file=file_obj
                )
                record_audit_event(
                    'statement.upload.accepted',
                    request=request,
                    actor=request.user,
                    target_type='statement',
                    target_id=statement.pk,
                    details={'file_size_bytes': file_obj.size},
                )
                transaction.on_commit(
                    lambda statement_id=statement.pk: process_statement_task.delay(
                        statement_id
                    )
                )
        except Exception:
            logger.exception('Could not queue statement for processing.')
            if statement is None:
                return Response(
                    {'error': 'The file could not be stored for processing.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            statement.processing_status = 'failed'
            statement.processing_error = 'Processing could not be queued.'
            statement.save(update_fields=['processing_status', 'processing_error'])
            record_audit_event(
                'statement.processing.enqueue_failed',
                request=request,
                actor=request.user,
                target_type='statement',
                target_id=statement.pk,
                outcome='failure',
            )
            return Response(
                {
                    'error': statement.processing_error,
                    'statement_id': statement.pk,
                    'processing_status': statement.processing_status,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                'message': 'Bank statement accepted for processing.',
                'statement_id': statement.pk,
                'processing_status': statement.processing_status,
                'status_url': reverse(
                    'statement_processing_status',
                    kwargs={'pk': statement.pk},
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class StatementProcessingStatusView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BankStatement.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        statement = self.get_object()
        return Response(
            {
                'statement_id': statement.pk,
                'processing_status': statement.processing_status,
                'is_processed': statement.is_processed,
                'error': statement.processing_error or None,
                'ai_evaluation': statement.ai_evaluation,
            },
            status=status.HTTP_200_OK,
        )


class TransactionListView(generics.ListAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.filter(statement__user=self.request.user)

        statement_id = self.request.query_params.get('statement_id')
        if statement_id:
            queryset = queryset.filter(statement_id=statement_id)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)

        search = self.request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(payee_payer__icontains=search) |
                Q(category__icontains=search)
            )

        ordering = self.request.query_params.get('ordering', '-date')
        if ordering in {'date', '-date', 'amount', '-amount'}:
            return queryset.order_by(ordering)

        return queryset.order_by('-date')


class TransactionDetailView(generics.RetrieveAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(statement__user=self.request.user)


class AnalyticsView(generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):

        statements = BankStatement.objects.filter(
            user=request.user, is_processed=True
        )
        evaluations = [
            {"id": s.id, "evaluation": s.ai_evaluation}
            for s in statements
            if s.ai_evaluation
        ]
        return Response({"evaluations": evaluations}, status=status.HTTP_200_OK)


class StatementBulkDeleteView(generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):

        statements = BankStatement.objects.filter(user=request.user)
        count = statements.count()

        # Delete physical files from the server
        for statement in statements:

            if statement.file:

                statement.file.delete(save=False)

        # Delete from DB (transactions are cascade-deleted)
        statements.delete()

        record_audit_event(
            'statement.bulk_deleted',
            request=request,
            actor=request.user,
            target_type='statement_collection',
            details={'count': count},
        )

        return Response(
            {
                "message": f"{count} bank statement(s) and all related transactions were deleted successfully."
            },
            status=status.HTTP_200_OK,
        )


class StatementFileDownloadView(APIView):
    """
    Serves the original uploaded PDF only to its owner. Media files must
    never be exposed via a public webserver/static route in production;
    this authenticated endpoint is the only supported way to retrieve them.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):

        try:

            statement = BankStatement.objects.get(pk=pk, user=request.user)

        except BankStatement.DoesNotExist:

            raise Http404

        if not statement.file:

            raise Http404

        record_audit_event(
            'statement.file_downloaded',
            request=request,
            actor=request.user,
            target_type='statement',
            target_id=statement.pk,
        )

        return FileResponse(
            statement.file.open("rb"),
            as_attachment=True,
            filename=statement.file.name.split("/")[-1],
            content_type="application/pdf",
        )


class AccountDeleteView(generics.GenericAPIView):
    """
    Permanently deletes the authenticated user's account, including all
    bank statements, transactions and uploaded PDF files (GDPR Art. 17 -
    right to erasure). Requires password confirmation.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AccountDeleteSerializer

    def delete(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["password"]):

            record_audit_event(
                'account.delete.rejected',
                request=request,
                actor=request.user,
                target_type='user',
                target_id=request.user.pk,
                outcome='failure',
            )

            return Response(
                {"error": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        record_audit_event(
            'account.deleted',
            request=request,
            actor=user,
            target_type='user',
            target_id=user.pk,
        )
        for statement in BankStatement.objects.filter(user=user):

            if statement.file:

                statement.file.delete(save=False)

        user.delete()  # cascades to statements/transactions

        return Response(
            {"message": "Your account and all associated data were permanently deleted."},
            status=status.HTTP_200_OK,
        )


class DataExportView(generics.GenericAPIView):
    """
    Returns all personal data stored about the authenticated user as JSON
    (GDPR Art. 15 - right of access / Art. 20 - data portability). Original
    PDF files can be retrieved individually via the file download endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):

        user = request.user
        statements = BankStatement.objects.filter(user=user).order_by("-id")

        data = {
            "user": {
                "username": user.username,
                "email": user.email,
                "date_joined": user.date_joined,
            },
            "statements": [
                {
                    **BankStatementSerializer(statement).data,
                    "file_download_url": f"/api/statements/{statement.id}/file/",
                }
                for statement in statements
            ],
        }
        record_audit_event(
            'data.exported',
            request=request,
            actor=user,
            target_type='user',
            target_id=user.pk,
            details={'statement_count': len(data['statements'])},
        )
        return Response(data, status=status.HTTP_200_OK)