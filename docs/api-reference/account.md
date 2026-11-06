---
layout: page
title: Account and Privacy Endpoints
permalink: /api-reference/account/
---

# Account and privacy endpoints

These endpoints cover user identity management and personal-data operations.

## Export personal data

```http
GET /api/auth/export/
Authorization: Bearer <access_token>
```

This returns a JSON document containing the authenticated user's information and the statements associated with the account. Each statement entry also includes a `file_download_url` that points to the protected file endpoint.

Example response:

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
      "is_processed": true,
      "ai_evaluation": "You had a stable month...",
      "transactions": [],
      "file_download_url": "/api/statements/1/file/"
    }
  ]
}
```

## Delete account

```http
DELETE /api/auth/account/
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request body:

```json
{
  "password": "StrongPass123!"
}
```

This route confirms the current password before deleting the account. It removes the user record and deletes all associated statements, transactions, and uploaded files in the media directory.

## Related pages

- [API overview]({{ '/api-reference/' | relative_url }})
- [Statement endpoints](./statements.html)
- [Transaction endpoints](./transactions.html)
