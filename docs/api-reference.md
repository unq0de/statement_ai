---
title: API Reference
layout: default
---

# API Reference

**Base URL (local):** `http://localhost:8000/api/` &nbsp;|&nbsp; **Format:** JSON (exception: file upload as `multipart/form-data`) &nbsp;|&nbsp; **Authentication:** JWT (Bearer Token)

## 1. Authentication

The API uses **JWT (JSON Web Tokens)** via [`djangorestframework-simplejwt`](https://django-rest-framework-simplejwt.readthedocs.io/).

After logging in, you receive an `access` and a `refresh` token. Send the `access` token with **every** request to a protected endpoint in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

| Token | Validity |
|---|---|
| Access Token | 60 minutes |
| Refresh Token | 1 day |

Once the access token expires, use the [refresh endpoint](#5-refresh-token) to obtain a new one without logging in again. All endpoints except registration and login require a valid access token — without one, the API responds with `401 Unauthorized`.

## 2. Endpoints Overview

| Method | Path | Auth Required | Description |
|---|---|---|---|
| ![POST](https://img.shields.io/badge/POST-2ea44f?style=flat-square) | `/api/auth/register/` | No | Register a new user |
| ![POST](https://img.shields.io/badge/POST-2ea44f?style=flat-square) | `/api/auth/login/` | No | Obtain access & refresh tokens |
| ![POST](https://img.shields.io/badge/POST-2ea44f?style=flat-square) | `/api/auth/refresh/` | No (refresh token required) | Obtain a new access token |
| ![DELETE](https://img.shields.io/badge/DELETE-d73a49?style=flat-square) | `/api/auth/account/` | Yes | Permanently delete your account and all associated data |
| ![GET](https://img.shields.io/badge/GET-0969da?style=flat-square) | `/api/auth/export/` | Yes | Export all personal data as JSON |
| ![GET](https://img.shields.io/badge/GET-0969da?style=flat-square) | `/api/statements/` | Yes | List your own bank statements |
| ![POST](https://img.shields.io/badge/POST-2ea44f?style=flat-square) | `/api/statements/upload/` | Yes | Upload a bank statement (PDF) & process it via AI |
| ![GET](https://img.shields.io/badge/GET-0969da?style=flat-square) | `/api/statements/analytics/` | Yes | AI evaluations of all processed bank statements |
| ![DELETE](https://img.shields.io/badge/DELETE-d73a49?style=flat-square) | `/api/statements/delete-all/` | Yes | Delete all your own bank statements + transactions |
| ![DELETE](https://img.shields.io/badge/DELETE-d73a49?style=flat-square) | `/api/statements/<int:pk>/` | Yes | Delete a single bank statement |
| ![GET](https://img.shields.io/badge/GET-0969da?style=flat-square) | `/api/statements/<int:pk>/file/` | Yes | Download the original PDF of a bank statement |
| ![GET](https://img.shields.io/badge/GET-0969da?style=flat-square) | `/api/transactions/` | Yes | List your own transactions |

<a id="3-register-a-user"></a>
<details>
<summary><b>3. Register a User</b></summary>

Creates a new user account.

**Endpoint:** `POST /api/auth/register/` · **Auth:** not required

**Request Body**

```json
{
  "username": "max.mustermann",
  "email": "max@example.com",
  "password": "ASecurePassword123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | Yes | Unique username |
| `email` | string | No | Email address |
| `password` | string | Yes | Must satisfy Django's password rules (minimum length, not too similar to the username, not a common password, not entirely numeric) |

**Response `201 Created`**

```json
{
  "username": "max.mustermann",
  "email": "max@example.com"
}
```

**Error Cases**

- `400 Bad Request` – Username already taken, password too weak, required field missing.

```json
{
  "password": ["This password is too common."]
}
```

</details>

<a id="4-login-obtain-token"></a>
<details>
<summary><b>4. Login (Obtain Token)</b></summary>

Exchanges username + password for a token pair.

**Endpoint:** `POST /api/auth/login/` · **Auth:** not required

**Request Body**

```json
{
  "username": "max.mustermann",
  "password": "ASecurePassword123"
}
```

**Response `200 OK`**

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error Cases**

- `401 Unauthorized` – Username or password incorrect.

</details>

<a id="5-refresh-token"></a>
<details>
<summary><b>5. Refresh Token</b></summary>

Issues a new access token from a valid refresh token.

**Endpoint:** `POST /api/auth/refresh/` · **Auth:** not required (refresh token in the body)

**Request Body**

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response `200 OK`**

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error Cases**

- `401 Unauthorized` – Refresh token expired or invalid, or the user it refers to no longer exists (e.g. account deleted, database reset) → user must log in again.

</details>

<a id="6-upload-a-bank-statement"></a>
<details>
<summary><b>6. Upload a Bank Statement</b></summary>

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

The individually detected transactions are **not** included directly in this response — retrieve them afterwards via [`GET /api/transactions/`](#10-list-transactions).

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

</details>

<a id="7-list-bank-statements"></a>
<details>
<summary><b>7. List Bank Statements</b></summary>

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

> Each bank statement is returned together with its associated transactions. You only ever see your own bank statements — other users' data is not visible. Note that the `file` path is only reachable directly when `DEBUG=1`; in production, use the [file download endpoint](#12-download-the-original-pdf) instead.

</details>

<a id="8-delete-a-bank-statement"></a>
<details>
<summary><b>8. Delete a Bank Statement</b></summary>

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

</details>

<a id="9-delete-all-bank-statements"></a>
<details>
<summary><b>9. Delete All Bank Statements</b></summary>

Permanently deletes **all** bank statements and transactions of the logged-in user, including the physical PDF files.

**Endpoint:** `DELETE /api/statements/delete-all/` · **Auth:** required

⚠️ **Warning:** This action cannot be undone.

**Response `200 OK`**

```json
{
  "message": "7 bank statement(s) and all related transactions were deleted successfully."
}
```

</details>

<a id="10-list-transactions"></a>
<details>
<summary><b>10. List Transactions</b></summary>

Lists all transactions from all bank statements of the logged-in user, sorted by date (newest first).

**Endpoint:** `GET /api/transactions/` · **Auth:** required

**Response `200 OK`**

```json
[
  {
    "id": 101,
    "date": "2026-07-01",
    "payee_payer": "ACME Corp",
    "description": "Monthly salary payment",
    "amount": "3200.00",
    "transaction_type": "INCOME",
    "category": "Salary & Main Income"
  },
  {
    "id": 100,
    "date": "2026-06-28",
    "payee_payer": "Netflix",
    "description": "Monthly subscription",
    "amount": "-15.99",
    "transaction_type": "CARD_PAYMENT",
    "category": "Subscriptions & Media"
  }
]
```

> There are currently no filter or pagination parameters — the endpoint always returns the complete list of all the user's transactions.

</details>

<a id="11-analytics-ai-evaluations"></a>
<details>
<summary><b>11. Analytics (AI Evaluations)</b></summary>

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

</details>

<a id="12-download-the-original-pdf"></a>
<details>
<summary><b>12. Download the Original PDF</b></summary>

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

</details>

<a id="13-export-my-data"></a>
<details>
<summary><b>13. Export My Data</b></summary>

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

</details>

<a id="14-delete-my-account"></a>
<details>
<summary><b>14. Delete My Account</b></summary>

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

</details>

<a id="15-data-models"></a>
<details>
<summary><b>15. Data Models</b></summary>

**BankStatement**

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique ID |
| `file` | string (URL) | Path/URL to the stored PDF file (use the [download endpoint](#12-download-the-original-pdf) in production) |
| `uploaded_at` | datetime (ISO 8601, UTC) | Upload timestamp; also the basis for the retention cleanup |
| `is_processed` | boolean | `true` once AI processing has completed successfully |
| `ai_evaluation` | string \| null | Free-text summary from the AI (always in English, max. 3 sentences, written directly to "you" in a friendly, professional financial-advisor tone) |
| `transactions` | Transaction[] | Associated transactions (only included in the list view) |

**Transaction**

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

</details>

<a id="16-error-format"></a>
<details>
<summary><b>16. Error Format</b></summary>

Errors are returned consistently as a JSON object with an `error` field (exception: registration validation errors, which are field-specific):

```json
{ "error": "Description of the error." }
```

| Status | Meaning |
|---|---|
| `400 Bad Request` | Invalid or missing input data |
| `401 Unauthorized` | Missing, invalid, or expired token |
| `404 Not Found` | Resource does not exist or belongs to another user |
| `500 Internal Server Error` | Unexpected server error (e.g. AI processing failed) |

> ℹ️ **Note:** A project-wide DRF exception handler guarantees this `{"error": "..."}` format even for cases DRF wouldn't normally catch cleanly — for example, a cryptographically valid refresh/access token whose underlying user no longer exists (deleted account, reset database, switched `DB_ENGINE`) is returned as a clean `401 Unauthorized` with `{"error": "Invalid or expired token."}` instead of an opaque `500`. All other unexpected exceptions are still logged server-side with a full traceback, but only ever exposed to the client as a generic `500` message.

</details>

<a id="17-typical-flow-end-to-end-example"></a>
<details open>
<summary><b>17. Typical Flow (End-to-End Example)</b></summary>

**1. Register**

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "max", "email": "max@example.com", "password": "ASecurePassword123!"}'
```

**2. Log in and obtain tokens**

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "max", "password": "ASecurePassword123!"}'
# -> { "access": "...", "refresh": "..." }
```

**3. Upload a bank statement**

```bash
curl -X POST http://localhost:8000/api/statements/upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@statement_july.pdf"
```

**4. View all bank statements**

```bash
curl http://localhost:8000/api/statements/ \
  -H "Authorization: Bearer <access_token>"
```

**5. View all transactions**

```bash
curl http://localhost:8000/api/transactions/ \
  -H "Authorization: Bearer <access_token>"
```

**6. View AI evaluations**

```bash
curl http://localhost:8000/api/statements/analytics/ \
  -H "Authorization: Bearer <access_token>"
```

**7. Download the original PDF of a statement**

```bash
curl -OJ http://localhost:8000/api/statements/14/file/ \
  -H "Authorization: Bearer <access_token>"
```

**8. Export all of my personal data**

```bash
curl http://localhost:8000/api/auth/export/ \
  -H "Authorization: Bearer <access_token>"
```

**9. Refresh the token once the access token expires**

```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

**10. Delete a single bank statement**

```bash
curl -X DELETE http://localhost:8000/api/statements/14/ \
  -H "Authorization: Bearer <access_token>"
```

**11. Delete all bank statements** *(warning: irreversible!)*

```bash
curl -X DELETE http://localhost:8000/api/statements/delete-all/ \
  -H "Authorization: Bearer <access_token>"
```

**12. Delete my entire account** *(warning: irreversible!)*

```bash
curl -X DELETE http://localhost:8000/api/auth/account/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "ASecurePassword123!"}'
```

</details>
