from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from statements.models import BankStatement


class Command(BaseCommand):
    help = (
        "Deletes bank statements (and their transactions/PDF files) that "
        "are older than settings.DATA_RETENTION_DAYS. Intended to be run "
        "regularly via cron, e.g. daily."
    )

    def handle(self, *args, **options):

        cutoff = timezone.now() - timedelta(days=settings.DATA_RETENTION_DAYS)
        expired = BankStatement.objects.filter(uploaded_at__lt=cutoff)
        count = expired.count()

        for statement in expired:

            if statement.file:

                statement.file.delete(save=False)

        expired.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} bank statement(s) older than "
                f"{settings.DATA_RETENTION_DAYS} days."
            )
        )
