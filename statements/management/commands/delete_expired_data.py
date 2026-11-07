from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from statements.models import (
    APIUsageRecord,
    AuditEvent,
    BankStatement,
    GeminiUsageRecord,
    TwoFactorLoginChallenge,
)


class Command(BaseCommand):
    help = (
        "Deletes expired bank statements, usage records, and audit events "
        "according to their configured retention periods. Intended to be "
        "run regularly via cron, e.g. daily."
    )

    def handle(self, *args, **options):

        now = timezone.now()
        cutoff = now - timedelta(days=settings.DATA_RETENTION_DAYS)
        expired = BankStatement.objects.filter(uploaded_at__lt=cutoff)
        count = expired.count()

        for statement in expired:

            if statement.file:

                statement.file.delete(save=False)

        expired.delete()

        usage_cutoff = now - timedelta(days=settings.API_USAGE_RETENTION_DAYS)
        api_usage_count, _ = APIUsageRecord.objects.filter(
            created_at__lt=usage_cutoff
        ).delete()
        gemini_usage_count, _ = GeminiUsageRecord.objects.filter(
            created_at__lt=usage_cutoff
        ).delete()
        audit_cutoff = now - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
        audit_count, _ = AuditEvent.objects.filter(
            created_at__lt=audit_cutoff
        ).delete()
        expired_challenges, _ = TwoFactorLoginChallenge.objects.filter(
            expires_at__lt=now
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} bank statement(s) older than "
                f"{settings.DATA_RETENTION_DAYS} days, "
                f"{api_usage_count} API usage record(s), and "
                f"{gemini_usage_count} Gemini usage record(s) older than "
                f"{settings.API_USAGE_RETENTION_DAYS} days, plus "
                f"{audit_count} audit event(s) older than "
                f"{settings.AUDIT_LOG_RETENTION_DAYS} days, and "
                f"{expired_challenges} expired 2FA challenge(s)."
            )
        )
