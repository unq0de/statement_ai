import logging

from celery import shared_task

from .audit import record_audit_event
from .models import BankStatement
from .services import process_pdf_statement_with_gemini

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
)
def process_statement_task(self, statement_id):
    statement = BankStatement.objects.get(pk=statement_id)
    if statement.processing_status == 'completed':
        return

    BankStatement.objects.filter(pk=statement_id).update(
        processing_status='processing',
        processing_error='',
    )
    statement.refresh_from_db()
    record_audit_event(
        'statement.processing.started',
        actor=statement.user,
        target_type='statement',
        target_id=statement.pk,
        details={'retry_count': self.request.retries},
    )

    try:
        process_pdf_statement_with_gemini(statement)
    except Exception as error:
        logger.exception('Statement processing failed for statement %s.', statement_id)
        if self.request.retries >= self.max_retries:
            BankStatement.objects.filter(pk=statement_id).update(
                processing_status='failed',
                processing_error='The file could not be processed.',
                is_processed=False,
            )
            record_audit_event(
                'statement.processing.failed',
                actor=statement.user,
                target_type='statement',
                target_id=statement.pk,
                outcome='failure',
                details={
                    'retry_count': self.request.retries,
                    'error_type': type(error).__name__,
                },
            )
        raise

    BankStatement.objects.filter(pk=statement_id).update(
        processing_status='completed',
        processing_error='',
        is_processed=True,
    )
    record_audit_event(
        'statement.processing.completed',
        actor=statement.user,
        target_type='statement',
        target_id=statement.pk,
    )