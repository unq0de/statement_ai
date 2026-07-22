# Statement AI

AI-powered REST API that reads bank statement PDFs, extracts and categorizes every transaction, and generates a financial summary — built with Django REST Framework and Google Gemini.

![Python](https://img.shields.io/badge/python-3.11-blue)
![Django](https://img.shields.io/badge/django-4.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.14-red)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-8E75B2)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Scheduled Data Retention Cleanup](#scheduled-data-retention-cleanup)
- [Privacy & GDPR](#privacy--gdpr)
- [API Reference](#api-reference)
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
  12. [Download the Original PDF](#12-download-the-original-pdf)
  13. [Export My Data](#13-export-my-data)
  14. [Delete My Account](#14-delete-my-account)
  15. [Data Models](#15-data-models)
  16. [Error Format](#16-error-format)
  17. [Typical Flow (End-to-End Example)](#17-typical-flow-end-to-end-example)
- [Project Structure](#project-structure)
- [License](#license)

---

## Features

- 🔐 JWT-based authentication (access + refresh tokens)
- 📄 PDF bank statement upload with type & size validation
- 🤖 Automatic transaction extraction and categorization via Google Gemini
- 📊 AI-generated financial summary per statement
- 🗂️ Per-user data isolation — every user only ever sees their own statements and transactions
- 🔒 Authenticated, ownership-checked file downloads — original PDFs are never publicly reachable
- 🗑️ Full account erasure and configurable data retention (GDPR Art. 17)
- 📤 Personal data export as JSON (GDPR Art. 15/20)
- 🐳 Fully dockerized (Django + PostgreSQL)

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4.2 + Django REST Framework |
| Auth | `djangorestframework-simplejwt` |
| Database | PostgreSQL 15 |
| AI | Google Gemini (`gemini-2.5-flash`) |
| Deployment | Docker / Docker Compose |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- A [Google Gemini API key](https://aistudio.google.com/apikey)

### Installation

```bash
git clone https://github.com/<your-username>/statement-ai.git
cd statement-ai
cp .env.example .env   # then fill in your own values
sudo docker compose up -d --build
sudo docker compose exec web python manage.py migrate
```

The API is then available at `http://localhost:8000/api/`.

### Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | `1` for development, `0` for production | `0` |
| `GEMINI_API_KEY` | Your Google Gemini API key | `AI...` |
| `POSTGRES_DB` | Database name | `statement_ai_db` |
| `POSTGRES_USER` | Database user | `statement_ai_user` |
| `POSTGRES_PASSWORD` | Database password | `********` |
| `ALLOWED_HOSTS` | Comma-separated hosts (production only) | `api.example.com` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins (production only) | `https://app.example.com` |
| `DATA_RETENTION_DAYS` | Days a bank statement is kept before it becomes eligible for automatic deletion | `365` |

> ⚠️ Never commit your `.env` file. Rotate `SECRET_KEY` and `GEMINI_API_KEY` immediately if they are ever exposed.

### Scheduled Data Retention Cleanup

Bank statements older than `DATA_RETENTION_DAYS` are cleaned up automatically by a dedicated `cron` service in `docker-compose.yml`. It runs the same image as `web`, but only executes `manage.py delete_expired_data` on a daily schedule (`cron/statement-ai-cron`, default `03:00`) and otherwise stays idle. It starts automatically with:

```bash
sudo docker compose up -d --build
```

Check that it's running and inspect its logs with:

```bash
sudo docker compose logs -f cron
```

To change the schedule, edit `cron/statement-ai-cron` and rebuild the `cron` service. You can also trigger a cleanup manually at any time — either via the `web` or the `cron` service, both share the same code and database:

```bash
sudo docker compose exec cron python manage.py delete_expired_data
```

This permanently deletes every bank statement (and its transactions and PDF file) whose `uploaded_at` is older than the configured retention period.

> If you'd rather not run the sidecar container, remove the `cron` service from `docker-compose.yml` and schedule `docker compose exec web python manage.py delete_expired_data` via the host's system cron instead.

---

## Privacy & GDPR

Statement AI processes financial data extracted from bank statements, which is personal data under the GDPR. The following measures are implemented:

- **Data minimization & retention** — statements are automatically eligible for deletion after `DATA_RETENTION_DAYS` (see above).
- **Right to erasure** — [`DELETE /api/auth/account/`](#14-delete-my-account) permanently removes the user account together with all statements, transactions, and uploaded PDF files.
- **Right of access / portability** — [`GET /api/auth/export/`](#13-export-my-data) returns all personal data held about the authenticated user as JSON.
- **Access control** — uploaded PDFs are never served from a public path. They can only be retrieved via the authenticated, ownership-checked [file download endpoint](#12-download-the-original-pdf).
- **Third-country data transfer** — bank statement content is sent to **Google Gemini** (Google LLC, USA) for AI processing. If you operate this API for real users in the EU/EEA, you are responsible for having a valid legal basis and a Data Processing Agreement (DPA) with Google covering this transfer before going to production.

This section describes the technical measures available in the API. It is not legal advice — consult a data protection professional before processing real users' financial data in production.

---

## API Reference

Statement AI is a REST API for uploading bank statements (PDF), which are automatically read, categorized, and converted into structured transactions using Google Gemini.

- **Base URL (local):** `http://localhost:8000/api/`
- **Format:** JSON (exception: file upload as `multipart/form-data`)
- **Authentication:** JWT (Bearer Token)

### 1. Authentication

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

### 2. Endpoints Overview

| Method | Path | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/auth/register/` | No | Register a new user |
| `POST` | `/api/auth/login/` | No | Obtain access & refresh tokens |
| `POST` | `/api/auth/refresh/` | No (refresh token required) | Obtain a new access token |
| `DELETE` | `/api/auth/account/` | Yes | Permanently delete your account and all associated data |
| `GET` | `/api/auth/export/` | Yes | Export all personal data as JSON |
| `GET` | `/api/statements/` | Yes | List your own bank statements |
| `POST` | `/api/statements/upload/` | Yes | Upload a bank statement (PDF) & process it via AI |
| `GET` | `/api/statements/analytics/` | Yes | AI evaluations of all processed bank statements |
| `DELETE` | `/api/statements/delete-all/` | Yes | Delete all your own bank statements + transactions |
| `DELETE` | `/api/statements/<int:pk>/` | Yes | Delete a single bank statement |
| `GET` | `/api/statements/<int:pk>/file/` | Yes | Download the original PDF of a bank statement |
| `GET` | `/api/transactions/` | Yes | List your own transactions |

### 3. Register a User

Creates a new user account.

**Endpoint:** `POST /api/auth/register/`
**Auth:** not required

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

### 4. Login (Obtain Token)

Exchanges username + password for a token pair.

**Endpoint:** `POST /api/auth/login/`
**Auth:** not required

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

### 5. Refresh Token

Issues a new access token from a valid refresh token.

**Endpoint:** `POST /api/auth/refresh/`
**Auth:** not required (refresh token in the body)

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

- `401 Unauthorized` – Refresh token expired or invalid → user must log in again.

### 6. Upload a Bank Statement

Uploads a PDF file, has it analyzed by Gemini AI, and automatically saves the detected transactions to the database. This request can take a few seconds depending on file size, since it waits synchronously for the AI response.

**Endpoint:** `POST /api/statements/upload/`
**Auth:** required
**Content-Type:** `multipart/form-data`

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
  "ai_evaluation": "This statement shows a healthy balance between income and recurring expenses. The primary income source is a monthly salary deposit of $3,200.00. Notable spending categories include Housing & Utilities and Groceries & Food..."
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
{ "error": "Only PDF files are allowed." }
```

### 7. List Bank Statements

Lists all bank statements of the logged-in user, newest first.

**Endpoint:** `GET /api/statements/`
**Auth:** required

**Response `200 OK`**

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

> Each bank statement is returned together with its associated transactions. You only ever see your own bank statements — other users' data is not visible. Note that the `file` path is only reachable directly when `DEBUG=1`; in production, use the [file download endpoint](#12-download-the-original-pdf) instead.

### 8. Delete a Bank Statement

Deletes a single bank statement, including its file and all associated transactions (cascade).

**Endpoint:** `DELETE /api/statements/<int:pk>/`
**Auth:** required

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

### 9. Delete All Bank Statements

Permanently deletes **all** bank statements and transactions of the logged-in user, including the physical PDF files.

**Endpoint:** `DELETE /api/statements/delete-all/`
**Auth:** required

⚠️ **Warning:** This action cannot be undone.

**Response `200 OK`**

```json
{
  "message": "7 bank statement(s) and all related transactions were deleted successfully."
}
```

### 10. List Transactions

Lists all transactions from all bank statements of the logged-in user, sorted by date (newest first).

**Endpoint:** `GET /api/transactions/`
**Auth:** required

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

### 11. Analytics (AI Evaluations)

Returns the AI-generated text evaluation (`ai_evaluation`) of all bank statements that have already been successfully processed.

**Endpoint:** `GET /api/statements/analytics/`
**Auth:** required

**Response `200 OK`**

```json
{
  "evaluations": [
    { "id": 14, "evaluation": "This statement shows a healthy balance..." },
    { "id": 12, "evaluation": "Spending was notably higher this month due to..." }
  ]
}
```

> Only includes bank statements with `is_processed = true` **and** an existing `ai_evaluation`. Statements that have not yet been processed, or that failed to upload, do not appear here.

### 12. Download the Original PDF

Streams the original uploaded PDF file of a bank statement. This is the only supported way to retrieve the file in production, since `/media/` is not publicly exposed there.

**Endpoint:** `GET /api/statements/<int:pk>/file/`
**Auth:** required

**Example**

```bash
curl -OJ http://localhost:8000/api/statements/14/file/ \
  -H "Authorization: Bearer <access_token>"
```

**Response `200 OK`** — binary PDF (`Content-Type: application/pdf`, downloaded as an attachment).

**Error Cases**

- `404 Not Found` – No bank statement with this ID, it belongs to another user, or it has no file attached.

### 13. Export My Data

Returns all personal data stored about the authenticated user — profile info plus every bank statement and its transactions — as a single JSON document (GDPR Art. 15 right of access / Art. 20 data portability). Original PDF files are referenced by download URL rather than embedded.

**Endpoint:** `GET /api/auth/export/`
**Auth:** required

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
      "ai_evaluation": "This statement shows a healthy balance...",
      "transactions": [ ],
      "file_download_url": "/api/statements/14/file/"
    }
  ]
}
```

### 14. Delete My Account

Permanently deletes the authenticated user's account, including all bank statements, transactions, and uploaded PDF files (GDPR Art. 17 right to erasure). Requires the current password as confirmation.

**Endpoint:** `DELETE /api/auth/account/`
**Auth:** required

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

⚠️ **Warning:** This action cannot be undone. The access/refresh tokens become invalid immediately since the underlying user no longer exists.

### 15. Data Models

**BankStatement**

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique ID |
| `file` | string (URL) | Path/URL to the stored PDF file (use the [download endpoint](#12-download-the-original-pdf) in production) |
| `uploaded_at` | datetime (ISO 8601, UTC) | Upload timestamp; also the basis for the retention cleanup |
| `is_processed` | boolean | `true` once AI processing has completed successfully |
| `ai_evaluation` | string \| null | Free-text summary from the AI (always in English) |
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

### 16. Error Format

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

### 17. Typical Flow (End-to-End Example)

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

# 7. Download the original PDF of a statement
curl -OJ http://localhost:8000/api/statements/14/file/ \
  -H "Authorization: Bearer <access_token>"

# 8. Export all of my personal data
curl http://localhost:8000/api/auth/export/ \
  -H "Authorization: Bearer <access_token>"

# 9. Refresh the token once the access token expires
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'

# 10. Delete a single bank statement
curl -X DELETE http://localhost:8000/api/statements/14/ \
  -H "Authorization: Bearer <access_token>"

# 11. Delete all bank statements (warning: irreversible!)
curl -X DELETE http://localhost:8000/api/statements/delete-all/ \
  -H "Authorization: Bearer <access_token>"

# 12. Delete my entire account (warning: irreversible!)
curl -X DELETE http://localhost:8000/api/auth/account/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "ASecurePassword123!"}'
```

---

## Project Structure

```
statement_ai/
├── statement_ai/          # Django project (settings, urls, wsgi)
├── statements/             # Main app
│   ├── models.py           # BankStatement & Transaction models
│   ├── serializers.py      # DRF serializers
│   ├── services.py         # Gemini AI integration
│   ├── views.py            # API views
│   ├── urls.py              # App-level routes
│   ├── management/
│   │   └── commands/
│   │       └── delete_expired_data.py   # GDPR retention cleanup command
│   └── migrations/
├── cron/
│   ├── entrypoint.sh        # Cron sidecar entrypoint
│   └── statement-ai-cron    # Crontab: daily retention cleanup schedule
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## License

This project is licensed under the [MIT License](LICENSE).