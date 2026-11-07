---
layout: page
title: Account and Privacy Endpoints
permalink: /api-reference/account/
---

# Account and privacy endpoints

These endpoints cover personal-data operations. Both require authentication.

## Export personal data

```http
GET /api/auth/export/
Authorization: Bearer <access_token>
```

Returns the authenticated user's profile and every statement with its transactions as one JSON document. PDFs are not embedded; each statement has a `file_download_url` pointing to the protected download endpoint.

```bash
curl http://localhost:8001/api/auth/export/ \
  -H "Authorization: Bearer <access_token>"
```

`200 OK`:

```json
{
  "user": {
    "username": "alice",
    "email": "alice@example.com",
    "date_joined": "2026-11-03T12:00:00Z"
  },
  "statements": [
    {
      "id": 1,
      "file": "/media/statements/2026/11/file.pdf",
      "uploaded_at": "2026-11-03T12:30:00Z",
      "processing_status": "completed",
      "is_processed": true,
      "ai_evaluation": "You had a stable month...",
      "transactions": [],
      "file_download_url": "/api/statements/1/file/"
    }
  ]
}
```

The export covers profile data and statements. It does not include usage records, audit events or two-factor data. The `file` value is a relative media path and is only reachable when `DEBUG=1`; use `file_download_url` instead.

## Delete the account

```http
DELETE /api/auth/account/
Authorization: Bearer <access_token>
Content-Type: application/json
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `password` | string | Yes | The current account password. |

```bash
curl -X DELETE http://localhost:8001/api/auth/account/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"password":"StrongPass123!"}'
```

`200 OK`:

```json
{ "message": "Your account and all associated data were permanently deleted." }
```

`400` with `{"error": "Incorrect password."}` if the password is wrong.

This deletes the user, all statements, all transactions and the stored PDF files, and it cannot be undone. Audit events about the deletion are kept, with their actor reference set to null. Deleting an account does not require a 2FA code.

## Related pages

- [API overview]({{ '/api-reference/' | relative_url }})
- [Authentication endpoints]({{ '/api-reference/authentication/' | relative_url }})
- [Statement endpoints]({{ '/api-reference/statements/' | relative_url }})
- [Security]({{ '/security/' | relative_url }})
