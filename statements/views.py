import logging

from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import BankStatement, Transaction
from .serializers import (
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