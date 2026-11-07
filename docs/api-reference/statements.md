---
layout: page
title: Statement Endpoints
permalink: /api-reference/statements/
---

# Statement endpoints

These routes manage the bank statements that belong to the authenticated user. All of them require authentication. A statement that does not exist or belongs to someone else returns `404`.

## Upload a statement

```http
POST /api/statements/upload/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `file` | file | Yes | A PDF of at most 10 MB. The field name `document` is accepted as an alternative. |

```bash
curl -X POST http://localhost:8001/api/statements/upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/statement.pdf"
```

`202 Accepted`:

```json
{
  "message": "Bank statement accepted for processing.",
  "statement_id": 1,
  "processing_status": "pending",
  "status_url": "/api/statements/1/status/"
}
```

The statement is stored and queued but not processed yet. Poll `status_url`.

Validation runs in this order, and the first failure wins:

1. A `file` or `document` part is present.
2. The declared content type is `application/pdf`, `application/octet-stream` or `binary/octet-stream`.
3. The content looks like a PDF: it starts with `%PDF`, or the filename ends in `.pdf` and `%PDF` appears in the first 2 KB. Empty files fail.
4. The size is at most 10 MB.

| Status | Body | Cause |
| --- | --- | --- |
| `400` | `{"error": "No file uploaded (field 'file' is required)."}` | No file part. |
| `400` | `{"error": "Only PDF files are allowed."}` | Content type not accepted. |
| `400` | `{"error": "Uploaded file is not a valid PDF."}` | Content check failed. |
| `400` | `{"error": "File too large (max. 10 MB)."}` | Over the size limit. |
| `401` | `{"detail": "..."}` | Missing or invalid token. |
| `429` | `{"error": "Rate limit exceeded."}` | More than 5 uploads in an hour. |
| `429` | `{"error": "Monthly statement processing limit reached.", "limit": 20, "used": 20}` | `GEMINI_MONTHLY_LIMIT_PER_USER` reached. `Retry-After` counts down to the start of next month. |
| `503` | `{"error": "The file could not be stored for processing."}` | Storing the file failed. |
| `503` | `{"error": "Processing could not be queued.", "statement_id": 1, "processing_status": "failed"}` | The file was stored but the job could not be queued, for example because Redis is down. The statement stays as `failed`. |

The monthly limit counts the user's existing statements uploaded in the current calendar month (UTC), whatever their status, so deleting a statement frees up quota. The content type is whatever the client declares; the content check in step 3 is what actually guards against non-PDF data.

## Check processing status

```http
GET /api/statements/<id>/status/
Authorization: Bearer <access_token>
```

```json
{
  "statement_id": 1,
  "processing_status": "completed",
  "is_processed": true,
  "error": null,
  "ai_evaluation": "You had a stable month..."
}
```

| `processing_status` | Meaning |
| --- | --- |
| `pending` | Accepted and queued, not picked up yet. |
| `processing` | A worker is working on it. This also stays set between automatic retries. |
| `completed` | Transactions and `ai_evaluation` are stored. |
| `failed` | Gave up. `error` is `"The file could not be processed."` or `"Processing could not be queued."` |

The real exception is only in the worker log and in the Gemini usage record, never in the API response.

## List statements

```http
GET /api/statements/
Authorization: Bearer <access_token>
```

| Query parameter | Values | Default | Description |
| --- | --- | --- | --- |
| `processed` | `1`, `true`, `yes`, `on` for true; any other value is false | none | Filters on `is_processed`. |
| `ordering` | `uploaded_at`, `-uploaded_at` | `-uploaded_at` | Other values fall back to the default. |

```bash
curl "http://localhost:8001/api/statements/?processed=true" \
  -H "Authorization: Bearer <access_token>"
```

`200 OK`, a JSON array. Each statement contains its transactions:

```json
[
  {
    "id": 1,
    "file": "http://localhost:8001/media/statements/2026/11/statement.pdf",
    "uploaded_at": "2026-11-03T14:47:12Z",
    "processing_status": "completed",
    "is_processed": true,
    "ai_evaluation": "You had a stable month...",
    "transactions": [
      {
        "id": 12,
        "date": "2026-10-05",
        "payee_payer": "Supermarket",
        "description": "Weekly groceries",
        "amount": "-65.40",
        "transaction_type": "CARD_PAYMENT",
        "category": "Groceries & Food"
      }
    ]
  }
]
```

The `file` value is a media URL that Django serves only when `DEBUG=1`. In production, use the download endpoint.

## Retrieve one statement

```http
GET /api/statements/<id>/
Authorization: Bearer <access_token>
```

Returns one statement in the same shape as a list item.

## Download the original PDF

```http
GET /api/statements/<id>/file/
Authorization: Bearer <access_token>
```

Streams the original file as an attachment with `Content-Type: application/pdf`. Returns `404` if the statement is not the caller's or has no file.

```bash
curl -OJ http://localhost:8001/api/statements/1/file/ \
  -H "Authorization: Bearer <access_token>"
```

## Delete one statement

```http
DELETE /api/statements/<id>/
Authorization: Bearer <access_token>
```

Deletes the statement, its transactions and its stored PDF.

```json
{ "message": "Bank statement and all related transactions were deleted successfully." }
```

## Delete all statements

```http
DELETE /api/statements/delete-all/
Authorization: Bearer <access_token>
```

Deletes every statement of the user, with transactions and PDFs. It cannot be undone.

```json
{ "message": "7 bank statement(s) and all related transactions were deleted successfully." }
```

## Analytics

```http
GET /api/statements/analytics/
Authorization: Bearer <access_token>
```

Also available at `GET /api/analytics/`. Returns the AI evaluation of every statement that is processed and has one.

```json
{
  "evaluations": [
    { "id": 1, "evaluation": "You had a stable month..." }
  ]
}
```

Nothing is aggregated and no ordering is applied. Statements that are pending, failed or have an empty evaluation are left out.

## Statement fields

| Field | Type | Description |
| --- | --- | --- |
| `id` | integer | |
| `file` | string | URL of the stored PDF. |
| `uploaded_at` | datetime, UTC | Also the basis for the retention cleanup. |
| `processing_status` | string | `pending`, `processing`, `completed` or `failed`. |
| `is_processed` | boolean | `true` once processing finished successfully. |
| `ai_evaluation` | string or null | At most three sentences, English, written to the user as "you". |
| `transactions` | array | See the [transaction fields]({{ '/api-reference/transactions/#transaction-fields' | relative_url }}). |

## Related pages

- [API overview]({{ '/api-reference/' | relative_url }})
- [Transaction endpoints]({{ '/api-reference/transactions/' | relative_url }})
- [Account and privacy endpoints]({{ '/api-reference/account/' | relative_url }})
- [Architecture]({{ '/architecture/#statement-processing' | relative_url }})
