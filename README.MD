# Statement AI – API Documentation

Statement AI is a REST API for uploading bank statements (PDF), which are automatically read, categorized, and converted into structured transactions using Google Gemini.

- **Base URL (local):** `http://localhost:8000/api/`
- **Format:** JSON (exception: file upload as `multipart/form-data`)
- **Authentication:** JWT (Bearer Token)

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Endpoints Overview](#2-endpoints-overview)
3. [Register a User](#3-register-a-user)
4. [Login (Obtain Token)](#4-login-obtain-token)
5. [Refresh Token](#5-refresh-token)
6. [Upload a Bank Statement](#6-upload-a-bank-statement)
7. [List Bank Statements](#7-list-bank-statements)
8. [Delete a Bank Statement](#8-delete-a-bank-statement)
9. [Delete All Bank Statements](#9-delete-all-bank-statements)
10. [List Transactions](#10-list-transactions)
11. [Analytics (AI Evaluations)](#11-analytics-ai-evaluations)
12. [Data Models](#12-data-models)
13. [Error Format](#13-error-format)
14. [Typical Flow (End-to-End Example)](#14-typical-flow-end-to-end-example)

---

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

Once the access token expires, use the [refresh endpoint](#5-refresh-token) to obtain a new one without logging in again.

All endpoints except registration and login require a valid access token. Without a (valid) token, the API responds with `401 Unauthorized`.

---

## 2. Endpoints Overview

| Method | Path | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/auth/register/` | No | Register a new user |
| `POST` | `/api/auth/login/` | No | Obtain access & refresh tokens |
| `POST` | `/api/auth/refresh/` | No (refresh token required) | Obtain a new access token |
| `GET` | `/api/statements/` | Yes | List your own bank statements |
| `POST` | `/api/statements/upload/` | Yes | Upload a bank statement (PDF) & process it via AI |
| `GET` | `/api/statements/analytics/` | Yes | AI evaluations of all processed bank statements |
| `DELETE` | `/api/statements/delete-all/` | Yes | Delete all your own bank statements + transactions |
| `DELETE` | `/api/statements/<int:pk>/` | Yes | Delete a single bank statement |
| `GET` | `/api/transactions/` | Yes | List your own transactions |

---

## 3. Register a User

Creates a new user account.

**Endpoint:** `POST /api/auth/register/`
**Auth:** not required

### Request Body

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

### Response `201 Created`

```json
{
  "username": "max.mustermann",
  "email": "max@example.com"
}
```

### Error Cases

- `400 Bad Request` – Username already taken, password too weak, required field missing.

```json
{
  "password": ["This password is too common."]
}
```

---

## 4. Login (Obtain Token)

Exchanges username + password for a token pair.

**Endpoint:** `POST /api/auth/login/`
**Auth:** not required

### Request Body

```json
{
  "username": "max.mustermann",
  "password": "ASecurePassword123"
}
```

### Response `200 OK`

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Error Cases

- `401 Unauthorized` – Username or password incorrect.

---

## 5. Refresh Token

Issues a new access token from a valid refresh token.

**Endpoint:** `POST /api/auth/refresh/`
**Auth:** not required (refresh token in the body)

### Request Body

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Response `200 OK`

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Error Cases

- `401 Unauthorized` – Refresh token expired or invalid → user must log in again.

---

## 6. Upload a Bank Statement

Uploads a PDF file, has it analyzed by Gemini AI, and automatically saves the detected transactions to the database. This request can take a few seconds depending on file size, since it waits synchronously for the AI response.

**Endpoint:** `POST /api/statements/upload/`
**Auth:** required
**Content-Type:** `multipart/form-data`

### Request

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes* | PDF file of the bank statement (max. 10 MB) |

\* A field named `document` is also accepted as an alternative.

**Constraints:**
- Only `application/pdf` is accepted.
- Maximum file size: **10 MB**.

### Example (cURL)

```bash
curl -X POST http://localhost:8000/api/statements/upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@statement_july.pdf"
```

### Response `201 Created`

```json
{
  "message": "Bank statement processed successfully.",
  "statement_id": 14,
  "ai_evaluation": "This statement shows a healthy balance between income and recurring expenses. The primary income source is a monthly salary deposit of $3,200.00. Notable spending categories include Housing & Utilities and Groceries & Food..."
}
```

The individually detected transactions are **not** included directly in this response — retrieve them afterwards via [`GET /api/transactions/`](#10-list-transactions).

### Error Cases

| Status | Cause |
|---|---|
| `400 Bad Request` | No file sent, wrong file type, or file > 10 MB |
| `401 Unauthorized` | Missing/invalid access token |
| `500 Internal Server Error` | AI processing failed (e.g. unreadable PDF). In this case the bank statement is automatically deleted again, so no incomplete records are left behind. |

```json
{ "error": "Only PDF files are allowed." }
```

---

## 7. List Bank Statements

Lists all bank statements of the logged-in user, newest first.

**Endpoint:** `GET /api/statements/`
**Auth:** required

### Response `200 OK`

```json
[
  {
    "id": 14,
    "file": "/media/statements/2026/07/statement_july.pdf",
    "uploaded_at": "2026-07-22T18:32:10Z",
    "is_processed": true,
    "ai_evaluation": "This statement shows a healthy balance...",
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

> Each bank statement is returned together with its associated transactions. You only ever see your own bank statements — other users' data is not visible.

---

## 8. Delete a Bank Statement

Deletes a single bank statement, including its file and all associated transactions (cascade).

**Endpoint:** `DELETE /api/statements/<int:pk>/`
**Auth:** required

### Example

```bash
curl -X DELETE http://localhost:8000/api/statements/14/ \
  -H "Authorization: Bearer <access_token>"
```

### Response `200 OK`

```json
{
  "message": "Bank statement and all related transactions were deleted successfully."
}
```

### Error Cases

- `404 Not Found` – No bank statement with this ID (or it belongs to another user).

---

## 9. Delete All Bank Statements

Permanently deletes **all** bank statements and transactions of the logged-in user, including the physical PDF files.

**Endpoint:** `DELETE /api/statements/delete-all/`
**Auth:** required

⚠️ **Warning:** This action cannot be undone.

### Response `200 OK`

```json
{
  "message": "7 bank statement(s) and all related transactions were deleted successfully."
}
```

---

## 10. List Transactions

Lists all transactions from all bank statements of the logged-in user, sorted by date (newest first).

**Endpoint:** `GET /api/transactions/`
**Auth:** required

### Response `200 OK`

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

---

## 11. Analytics (AI Evaluations)

Returns the AI-generated text evaluation (`ai_evaluation`) of all bank statements that have already been successfully processed.

**Endpoint:** `GET /api/statements/analytics/`
**Auth:** required

### Response `200 OK`

```json
{
  "evaluations": [
    { "id": 14, "evaluation": "This statement shows a healthy balance..." },
    { "id": 12, "evaluation": "Spending was notably higher this month due to..." }
  ]
}
```

> Only includes bank statements with `is_processed = true` **and** an existing `ai_evaluation`. Statements that have not yet been processed, or that failed to upload, do not appear here.

---

## 12. Data Models

### BankStatement

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique ID |
| `file` | string (URL) | Path/URL to the stored PDF file |
| `uploaded_at` | datetime (ISO 8601, UTC) | Upload timestamp |
| `is_processed` | boolean | `true` once AI processing has completed successfully |
| `ai_evaluation` | string \| null | Free-text summary from the AI (always in English) |
| `transactions` | Transaction[] | Associated transactions (only included in the list view) |

### Transaction

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

---

## 13. Error Format

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

---

## 14. Typical Flow (End-to-End Example)

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "max", "email": "max@example.com", "password": "ASecurePassword123!"}'

# 2. Log in and obtain tokens
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "max", "password": "ASecurePassword123!"}'
# -> { "access": "...", "refresh": "..." }

# 3. Upload a bank statement
curl -X POST http://localhost:8000/api/statements/upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@statement_july.pdf"

# 4. View all bank statements
curl http://localhost:8000/api/statements/ \
  -H "Authorization: Bearer <access_token>"

# 5. View all transactions
curl http://localhost:8000/api/transactions/ \
  -H "Authorization: Bearer <access_token>"

# 6. View AI evaluations
curl http://localhost:8000/api/statements/analytics/ \
  -H "Authorization: Bearer <access_token>"

# 7. Refresh the token once the access token expires
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'

# 8. Delete a single bank statement
curl -X DELETE http://localhost:8000/api/statements/14/ \
  -H "Authorization: Bearer <access_token>"

# 9. Delete everything (warning: irreversible!)
curl -X DELETE http://localhost:8000/api/statements/delete-all/ \
  -H "Authorization: Bearer <access_token>"
```