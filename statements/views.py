import logging
import math
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import BankStatement, Transaction
from .serializers import (
    AccountDeleteSerializer,
    BankStatementSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordRevokingTokenRefreshSerializer,
    RateLimitedTokenObtainPairSerializer,
    TransactionSerializer,
    UserRegistrationSerializer,
)
from .services import process_pdf_statement_with_gemini
from .throttles import FailedLoginThrottle

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


class LoginView(TokenObtainPairView):

    serializer_class = RateLimitedTokenObtainPairSerializer
    throttle_classes = [FailedLoginThrottle]


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

        if users.count() == 1:
            self._send_reset_email(users.first())

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
            instructions = f'Reset your password using this link:\n{reset_link}'
        else:
            instructions = (
                'Submit these values to POST /api/auth/password-reset/confirm/:\n'
                f'uid: {uid}\ntoken: {token}'
            )

        expiry_minutes = max(1, math.ceil(settings.PASSWORD_RESET_TIMEOUT / 60))
        message = (
            'A password reset was requested for your account.\n\n'
            f'{instructions}\n\n'
            f'This link expires in {expiry_minutes} minutes. '
            'If you did not request this change, you can ignore this email.'
        )

        try:
            delivered = send_mail(
                subject='Reset your password',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
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
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=validated_data['user'].pk)
            if not default_token_generator.check_token(user, validated_data['token']):
                return Response(
                    {'error': 'This password reset link is invalid or expired.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(validated_data['new_password'])
            user.save(update_fields=['password'])

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

        statement = BankStatement.objects.create(
            user=request.user, file=file_obj
        )

        try:

            process_pdf_statement_with_gemini(statement)

        except Exception:

            logger.exception("Error while processing statement %s", statement.id)
            statement.delete()
            return Response(
                {"error": "The file could not be processed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Bank statement processed successfully.",
                "statement_id": statement.id,
                "ai_evaluation": statement.ai_evaluation,
            },
            status=status.HTTP_201_CREATED,
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

            return Response(
                {"error": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
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
        return Response(data, status=status.HTTP_200_OK)