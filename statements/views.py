import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BankStatement, Transaction
from .serializers import (
    AccountDeleteSerializer,
    BankStatementSerializer,
    TransactionSerializer,
    UserRegistrationSerializer,
)
from .services import process_pdf_statement_with_gemini

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# ------------------------------------------------------------------
# Views
# ------------------------------------------------------------------


class RegisterView(generics.CreateAPIView):

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer


class StatementListView(generics.ListAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankStatementSerializer

    def get_queryset(self):

        return BankStatement.objects.filter(
            user=self.request.user
        ).order_by("-id")


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

        if file_obj.content_type != "application/pdf":
            return Response(
                {"error": "Only PDF files are allowed."},
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

        return Transaction.objects.filter(
            statement__user=self.request.user
        ).order_by("-date")


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


class StatementDeleteView(generics.DestroyAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        return BankStatement.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):

        if instance.file:

            instance.file.delete(save=False)
        instance.delete()

    def destroy(self, request, *args, **kwargs):

        super().destroy(request, *args, **kwargs)
        return Response(
            {
                "message": "Bank statement and all related transactions were deleted successfully."
            },
            status=status.HTTP_200_OK,
        )


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