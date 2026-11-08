import json
import logging
import time

from django.conf import settings
from django.db import transaction as db_transaction

from .models import BankStatement, GeminiUsageRecord, Transaction

logger = logging.getLogger(__name__)

# Allowed transaction categories and types - must match Gemini prompt
ALLOWED_CATEGORIES = {
    "Housing & Utilities",
    "Groceries & Food",
    "Dining Out & Cafes",
    "Transportation",
    "Shopping & Retail",
    "Subscriptions & Media",
    "Health & Medical",
    "Financial & Insurance",
    "Salary & Main Income",
    "Secondary Income",
    "Transfers & P2P",
    "Education & Childcare",
    "Travel & Vacations",
    "Cash & ATM",
    "Miscellaneous & Other",
}

try:
    from google import genai as google_genai
    from google.genai import types
except ImportError:  # pragma: no cover - dependency is optional for offline tests.
    google_genai = None
    types = None


def _get_gemini_client():
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    if google_genai is None:
        raise RuntimeError("Google Gemini SDK is not installed.")

    return google_genai.Client(api_key=settings.GEMINI_API_KEY)


def _token_count(usage_metadata, name):
    value = getattr(usage_metadata, name, None)
    try:
        return max(0, int(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def _record_gemini_usage(statement, model_name, status, started_at, response=None, error=None):
    if not settings.API_USAGE_TRACKING_ENABLED:
        return

    usage_metadata = getattr(response, 'usage_metadata', None)
    try:
        GeminiUsageRecord.objects.create(
            user_id=statement.user_id,
            statement=statement,
            model_name=model_name,
            status=status,
            prompt_tokens=_token_count(usage_metadata, 'prompt_token_count'),
            completion_tokens=_token_count(usage_metadata, 'candidates_token_count'),
            total_tokens=_token_count(usage_metadata, 'total_token_count'),
            duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            error_type=type(error).__name__ if error else '',
        )
    except Exception:
        logger.exception('Could not save Gemini usage for statement %s.', statement.pk)


def process_pdf_statement_with_gemini(statement_instance):
    """Extracts transactions from a bank statement PDF with Gemini and stores the
    results in English in the database.
    """
    client = _get_gemini_client()

    pdf_bytes = statement_instance.file.read()

    prompt = """
    You are an expert financial AI data extractor. Analyze the attached bank statement PDF and return a JSON response.

    CRITICAL REQUIREMENTS:
    1. STRICT LANGUAGE REQUIREMENT: All output fields, summaries, descriptions, and evaluation text MUST BE IN ENGLISH ONLY. Do NOT use German or any other language under any circumstances.
    2. CONTENT LENGHT: The AI evaluation must be comprehensive, covering all transactions, and should provide a clear summary of the user's financial situation based on the statement in three sentences at maximum.
    3. SPEECH STYLE: In the whole evaluation use "you" for the user instead of the whole name and writing in third person is strictly forbidden. The evaluation should be written in a friendly and professional tone, as if you were a financial advisor giving advice to the user.
    4. RETURN ONLY VALID JSON. No Markdown formatting block wrappers (do NOT use ```json ... ```), just plain raw JSON.

    ALLOWED CATEGORIES (Pick EXACTLY ONE per transaction):
    - Housing & Utilities
    - Groceries & Food
    - Dining Out & Cafes
    - Transportation
    - Shopping & Retail
    - Subscriptions & Media
    - Health & Medical
    - Financial & Insurance
    - Salary & Main Income
    - Secondary Income
    - Transfers & P2P
    - Education & Childcare
    - Travel & Vacations
    - Cash & ATM
    - Miscellaneous & Other

    ALLOWED TRANSACTION TYPES (Pick EXACTLY ONE per transaction):
    - INCOME
    - TRANSFER_OUT
    - TRANSFER_IN
    - DIRECT_DEBIT
    - STANDING_ORDER
    - CARD_PAYMENT
    - ATM_WITHDRAWAL
    - FEE_CHARGE

    JSON STRUCTURE:
    {
      "ai_evaluation": "A comprehensive financial evaluation and summary of this bank statement written strictly in English.",
      "transactions": [
        {
          "date": "YYYY-MM-DD",
          "amount": -45.50,
          "payee_payer": "Name of sender or recipient",
          "description": "Short explanation or booking details in English",
          "transaction_type": "ONE OF THE ALLOWED TRANSACTION TYPES",
          "category": "ONE OF THE ALLOWED CATEGORIES"
        }
      ]
    }

    Note for amount: Outgoing payments MUST be negative numbers (e.g. -12.50). Incoming payments MUST be positive numbers (e.g. 1500.00).
    """

    model_name = settings.GEMINI_MODEL
    started_at = time.monotonic()
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                prompt,
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            ],
        )
    except Exception as error:
        _record_gemini_usage(
            statement_instance,
            model_name,
            'failed',
            started_at,
            error=error,
        )
        raise

    _record_gemini_usage(
        statement_instance,
        model_name,
        'succeeded',
        started_at,
        response=response,
    )

    response_text = getattr(response, 'text', '')
    if not response_text:
        response_text = str(response)
    response_text = response_text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    data = json.loads(response_text.strip())

    transactions_data = data.get("transactions", [])
    
    # Validate transaction data for financial accuracy
    validated_transactions = []
    for i, tx in enumerate(transactions_data):
        # Validate required fields
        if not tx.get("date"):
            logger.warning(
                'Skipping transaction %d in statement %s: missing required field "date".',
                i, statement_instance.pk
            )
            continue
        if tx.get("amount") is None or tx.get("amount") == "":
            logger.warning(
                'Skipping transaction %d in statement %s: missing required field "amount".',
                i, statement_instance.pk
            )
            continue
        
        # Validate types and format
        try:
            # Ensure amount can be converted to Decimal
            amount_value = float(tx.get("amount"))
        except (ValueError, TypeError):
            logger.warning(
                'Skipping transaction %d in statement %s: invalid amount format "%s".',
                i, statement_instance.pk, tx.get("amount")
            )
            continue
        
        # Validate transaction type
        valid_types = dict(Transaction.TYPE_CHOICES)
        tx_type = tx.get("transaction_type", "FEE_CHARGE")
        if tx_type not in valid_types:
            logger.warning(
                'Skipping transaction %d in statement %s: invalid transaction_type "%s".',
                i, statement_instance.pk, tx_type
            )
            continue
        
        # Validate category (warn but don't skip - use default)
        category = tx.get("category", "Miscellaneous & Other")
        if category not in ALLOWED_CATEGORIES:
            logger.warning(
                'Transaction %d in statement %s has category "%s" not in allowed list. Using default.',
                i, statement_instance.pk, category
            )
            category = "Miscellaneous & Other"
        
        validated_transactions.append(
            Transaction(
                statement=statement_instance,
                date=tx.get("date"),
                amount=amount_value,
                payee_payer=tx.get("payee_payer", ""),
                description=tx.get("description", ""),
                transaction_type=tx_type,
                category=category,
            )
        )
    
    with db_transaction.atomic():
        Transaction.objects.filter(statement=statement_instance).delete()
        statement_instance.ai_evaluation = data.get("ai_evaluation", "")
        statement_instance.is_processed = True
        statement_instance.save(update_fields=["ai_evaluation", "is_processed"])

        if validated_transactions:
            Transaction.objects.bulk_create(validated_transactions)

    return statement_instance