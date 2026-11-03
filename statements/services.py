import json

from django.conf import settings

from .models import BankStatement, Transaction

try:
    from google import genai as google_genai
except ImportError:  # pragma: no cover - dependency is optional for offline tests.
    google_genai = None


def _get_gemini_model():
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    if google_genai is None:
        raise RuntimeError("Google Gemini SDK is not installed.")

    client = google_genai.Client(api_key=settings.GEMINI_API_KEY)
    return client.models


def process_pdf_statement_with_gemini(statement_instance):
    """Extracts transactions from a bank statement PDF with Gemini and stores the
    results in English in the database.
    """
    model = _get_gemini_model()

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

    try:
        response = model.generate_content(
            [prompt, {"mime_type": "application/pdf", "data": pdf_bytes}]
        )
    except TypeError:
        response = model.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, {"mime_type": "application/pdf", "data": pdf_bytes}],
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

    statement_instance.ai_evaluation = data.get("ai_evaluation", "")
    statement_instance.is_processed = True
    statement_instance.save()

    transactions_data = data.get("transactions", [])
    for tx in transactions_data:
        Transaction.objects.create(
            statement=statement_instance,
            date=tx.get("date"),
            amount=tx.get("amount", 0.0),
            payee_payer=tx.get("payee_payer", ""),
            description=tx.get("description", ""),
            transaction_type=tx.get("transaction_type", "FEE_CHARGE"),
            category=tx.get("category", "Miscellaneous & Other"),
        )

    return statement_instance