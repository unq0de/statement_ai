---
layout: page
title: Statement Endpoints
permalink: /api-reference/statements/
---

# Statement endpoints

These routes manage the bank statements that belong to the authenticated user.

## List statements

```http
GET /api/statements/
Authorization: Bearer <access_token>
```

Optional query parameters:

- `processed=true` or `processed=false`
- `ordering=uploaded_at` or `-uploaded_at`

Example:

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8001/api/statements/?processed=true
```

Example response:

```json
[
  {
    "id": 1,
    "file": "/media/statements/2026/11/statement.pdf",
    "uploaded_at": "2026-11-03T14:47:12Z",
    "processing_status": "completed",
    "is_processed": true,
    "ai_evaluation": "You had a stable month...",
    "transactions": []
  }
]
```

## Upload a statement

```http
POST /api/statements/upload/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

Form field:

- `file`: the PDF file to process

Example:

```bash
curl -X POST \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/statement.pdf" \
  http://localhost:8001/api/statements/upload/
```

The upload endpoint validates the file, stores it, and queues background processing:

- the file must be a PDF
- the content must look like a real PDF header
- the file must be under 10 MB
- the request must be authenticated

Accepted response (`202 Accepted`):

```json
{
  "message": "Bank statement accepted for processing.",
  "statement_id": 1,
  "processing_status": "pending",
  "status_url": "/api/statements/1/status/"
}
```

Poll `status_url` until `processing_status` is `completed` or `failed`. The status endpoint returns the evaluation when processing is complete and a safe error message if processing ultimately fails:

```http
GET /api/statements/<id>/status/
Authorization: Bearer <access_token>
```

```json
{
  "statement_id": 1,
  "processing_status": "processing",
  "is_processed": false,
  "error": null,
  "ai_evaluation": null
}
```

Processing states are `pending`, `processing`, `completed`, and `failed`. Invalid files still receive an immediate `400 Bad Request`. If the queue is unavailable, the upload returns `503 Service Unavailable` and the statement status is `failed`.

## Retrieve one statement

```http
GET /api/statements/<id>/
Authorization: Bearer <access_token>
```

Example response:

```json
{
  "id": 1,
  "file": "/media/statements/2026/11/statement.pdf",
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
      "amount": -65.4,
      "transaction_type": "CARD_PAYMENT",
      "category": "Groceries & Food"
    }
  ]
}
```

## Download the original PDF

```http
GET /api/statements/<id>/file/
Authorization: Bearer <access_token>
```

This route streams the original file as an attachment. It is only available for the statement owner.

## Delete one statement

```http
DELETE /api/statements/<id>/
Authorization: Bearer <access_token>
```

Response:

```json
{
  "message": "Bank statement and all related transactions were deleted successfully."
}
```

## Delete all statements

```http
DELETE /api/statements/delete-all/
Authorization: Bearer <access_token>
```

This deletes every bank statement owned by the logged-in user, including all related transactions and local PDF files.

## Analytics

```http
GET /api/statements/analytics/
Authorization: Bearer <access_token>
```

Example response:

```json
{
  "evaluations": [
    {
      "id": 1,
      "evaluation": "You had a stable month..."
    }
  ]
}
```

## Related pages

- [API overview]({{ '/api-reference/' | relative_url }})
- [Transaction endpoints](./transactions.html)
- [Account and privacy endpoints](./account.html)
