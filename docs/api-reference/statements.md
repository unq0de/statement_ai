---
title: API Reference — Bank Statements
permalink: /api-reference/statements/
---

# Bank Statements
{: #bank-statements }

All endpoints on this page require a valid `access` token (see [Authentication]({{ '/api-reference/' | relative_url }}#authentication)).

## Upload a Bank Statement
{: #upload-a-bank-statement }

Uploads a PDF file, has it analyzed by Gemini AI, and automatically saves the detected transactions to the database. This request can take a few seconds depending on file size, since it waits synchronously for the AI response.

**Endpoint:** `POST /api/statements/upload/` · **Auth:** required · **Content-Type:** `multipart/form-data`

**Request**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes* | PDF file of the bank statement (max. 10 MB) |

\* A field named `document` is also accepted as an alternative.

**Constraints:**
- Only `application/pdf` is accepted.
- Maximum file size: **10 MB**.

**Example (cURL)**

```bash
curl -X POST http://localhost:8000/api/statements/upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@statement_july.pdf"
```

**Response `201 Created`**

```json
{
  "message": "Bank statement processed successfully.",
  "statement_id": 14,
  "ai_evaluation": "Your finances look healthy this month, with your salary of $3,200.00 comfortably covering your regular expenses. Most of your spending went toward Housing & Utilities and Groceries & Food. Keep an eye on your subscriptions, as they're adding up steadily each month."
}
```

The individually detected transactions are **not** included directly in this response — retrieve them afterwards via [`GET /api/transactions/`]({{ '/api-reference/transactions/' | relative_url }}#list-transactions).

**Error Cases**

| Status | Cause |
|---|---|
| `400 Bad Request` | No file sent, wrong file type, or file > 10 MB |
| `401 Unauthorized` | Missing/invalid access token |
| `500 Internal Server Error` | AI processing failed (e.g. unreadable PDF). In this case the bank statement is automatically deleted again, so no incomplete records are left behind. |

```json
{ "error": "No file uploaded (field 'file' is required)." }
```

```json
{ "error": "Only PDF files are allowed." }
```

```json
{ "error": "File too large (max. 10 MB)." }
```

## List Bank Statements
{: #list-bank-statements }

Lists all bank statements of the logged-in user, newest first.

**Endpoint:** `GET /api/statements/` · **Auth:** required

**Response `200 OK`**

```json
[
  {
    "id": 14,
    "file": "/media/statements/2026/07/statement_july.pdf",
    "uploaded_at": "2026-07-22T18:32:10Z",
    "is_processed": true,
    "ai_evaluation": "Your finances look healthy this month, with your salary comfortably covering your regular expenses...",
    "transactions": [
      {
        "id": 101,
        "date": "2026-07-01",
        "payee_payer": "ACME Corp",
        "description": "Monthly salary payment",
        "amount": "3200.00",
        "transaction_type": "INCOME",
        "category": "Salary & Main Income"
      }
    ]
  }
]
```

> Each bank statement is returned together with its associated transactions. You only ever see your own bank statements — other users' data is not visible. Note that the `file` path is only reachable directly when `DEBUG=1`; in production, use the [file download endpoint](#download-the-original-pdf) instead.

## Delete a Bank Statement
{: #delete-a-bank-statement }

Deletes a single bank statement, including its file and all associated transactions (cascade).

**Endpoint:** `DELETE /api/statements/<int:pk>/` · **Auth:** required

**Example**

```bash
curl -X DELETE http://localhost:8000/api/statements/14/ \
  -H "Authorization: Bearer <access_token>"
```

**Response `200 OK`**

```json
{
  "message": "Bank statement and all related transactions were deleted successfully."
}
```

**Error Cases**

- `404 Not Found` – No bank statement with this ID (or it belongs to another user).

## Delete All Bank Statements
{: #delete-all-bank-statements }

Permanently deletes **all** bank statements and transactions of the logged-in user, including the physical PDF files.

**Endpoint:** `DELETE /api/statements/delete-all/` · **Auth:** required

⚠️ **Warning:** This action cannot be undone.

**Response `200 OK`**

```json
{
  "message": "7 bank statement(s) and all related transactions were deleted successfully."
}
```

## Analytics (AI Evaluations)
{: #analytics-ai-evaluations }

Returns the AI-generated text evaluation (`ai_evaluation`) of all bank statements that have already been successfully processed.

**Endpoint:** `GET /api/statements/analytics/` · **Auth:** required

**Response `200 OK`**

```json
{
  "evaluations": [
    { "id": 14, "evaluation": "Your finances look healthy this month, with your salary comfortably covering your regular expenses..." },
    { "id": 12, "evaluation": "Your spending was notably higher this month, mainly due to..." }
  ]
}
```

> Only includes bank statements with `is_processed = true` **and** an existing `ai_evaluation`. Statements that have not yet been processed, or that failed to upload, do not appear here.

## Download the Original PDF
{: #download-the-original-pdf }

Streams the original uploaded PDF file of a bank statement. This is the only supported way to retrieve the file in production, since `/media/` is not publicly exposed there.

**Endpoint:** `GET /api/statements/<int:pk>/file/` · **Auth:** required

**Example**

```bash
curl -OJ http://localhost:8000/api/statements/14/file/ \
  -H "Authorization: Bearer <access_token>"
```

**Response `200 OK`** — binary PDF (`Content-Type: application/pdf`, downloaded as an attachment).

**Error Cases**

- `404 Not Found` – No bank statement with this ID, it belongs to another user, or it has no file attached.

---

Next: [Transactions]({{ '/api-reference/transactions/' | relative_url }}) covers listing individual transactions across all statements.
