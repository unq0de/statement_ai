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

The upload endpoint enforces a few checks before processing:

- the file must be a PDF
- the content must look like a real PDF header
- the file must be under 10 MB
- the request must be authenticated

Successful response:

```json
{
  "message": "Bank statement processed successfully.",
  "statement_id": 1,
  "ai_evaluation": "You had a stable month..."
}
```

If the file is invalid or the AI processing fails, the API returns an error response instead of storing a broken record.

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
