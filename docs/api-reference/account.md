---
title: API Reference — Account & Personal Data
permalink: /api-reference/account/
---

# Account & Personal Data
{: #account-personal-data }

These two endpoints implement the GDPR rights described on the [Privacy & GDPR]({{ '/privacy-gdpr/' | relative_url }}) page.

## Export My Data
{: #export-my-data }

Returns all personal data stored about the authenticated user — profile info plus every bank statement and its transactions — as a single JSON document (GDPR Art. 15 right of access / Art. 20 data portability). Original PDF files are referenced by download URL rather than embedded.

**Endpoint:** `GET /api/auth/export/` · **Auth:** required

**Response `200 OK`**

```json
{
  "user": {
    "username": "max.mustermann",
    "email": "max@example.com",
    "date_joined": "2026-01-10T09:15:00Z"
  },
  "statements": [
    {
      "id": 14,
      "file": "/media/statements/2026/07/statement_july.pdf",
      "uploaded_at": "2026-07-22T18:32:10Z",
      "is_processed": true,
      "ai_evaluation": "Your finances look healthy this month, with your salary comfortably covering your regular expenses...",
      "transactions": [ ],
      "file_download_url": "/api/statements/14/file/"
    }
  ]
}
```

## Delete My Account
{: #delete-my-account }

Permanently deletes the authenticated user's account, including all bank statements, transactions, and uploaded PDF files (GDPR Art. 17 right to erasure). Requires the current password as confirmation.

**Endpoint:** `DELETE /api/auth/account/` · **Auth:** required

**Request Body**

```json
{ "password": "ASecurePassword123" }
```

**Response `200 OK`**

```json
{ "message": "Your account and all associated data were permanently deleted." }
```

**Error Cases**

- `400 Bad Request` – Password missing or incorrect.

```json
{ "error": "Incorrect password." }
```

⚠️ **Warning:** This action cannot be undone. The access/refresh tokens become invalid immediately since the underlying user no longer exists.

---

Next: [Data Models]({{ '/data-models/' | relative_url }}) describes the exact shape of `BankStatement` and `Transaction` objects.
