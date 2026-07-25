---
title: Data Models
permalink: /data-models/
---

# Data Models
{: #data-models }

## BankStatement
{: #bankstatement }

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique ID |
| `file` | string (URL) | Path/URL to the stored PDF file (use the [download endpoint]({{ '/api-reference/statements/' | relative_url }}#download-the-original-pdf) in production) |
| `uploaded_at` | datetime (ISO 8601, UTC) | Upload timestamp; also the basis for the retention cleanup |
| `is_processed` | boolean | `true` once AI processing has completed successfully |
| `ai_evaluation` | string \| null | Free-text summary from the AI (always in English, max. 3 sentences, written directly to "you" in a friendly, professional financial-advisor tone) |
| `transactions` | Transaction[] | Associated transactions (only included in the list view) |

## Transaction
{: #transaction }

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique ID |
| `date` | string (`YYYY-MM-DD`) | Booking date |
| `payee_payer` | string | Name of the payee or payer |
| `description` | string | Short description of the booking (in English) |
| `amount` | string (decimal) | Amount. **Negative** = outgoing payment, **positive** = incoming payment |
| `transaction_type` | string (enum) | One of: `INCOME`, `TRANSFER_OUT`, `TRANSFER_IN`, `DIRECT_DEBIT`, `STANDING_ORDER`, `CARD_PAYMENT`, `ATM_WITHDRAWAL`, `FEE_CHARGE` |
| `category` | string (enum) | One of: `Housing & Utilities`, `Groceries & Food`, `Dining Out & Cafes`, `Transportation`, `Shopping & Retail`, `Subscriptions & Media`, `Health & Medical`, `Financial & Insurance`, `Salary & Main Income`, `Secondary Income`, `Transfers & P2P`, `Education & Childcare`, `Travel & Vacations`, `Cash & ATM`, `Miscellaneous & Other` |

> All AI-generated text (`description`, `ai_evaluation`) is always in **English**, regardless of the language of the original PDF.

> ℹ️ **Note:** `transaction_type` is a real database-level enum (Django `choices`). `category`, however, is a free-text field at the database level (default `"Uncategorized"`) — the 15 categories above are enforced only by the instructions given to Gemini in the AI prompt, not by a DB constraint.

---

Next: [Error Format]({{ '/api-reference/errors/' | relative_url }}) describes how errors are shaped across every endpoint.
