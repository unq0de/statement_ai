---
title: Documentation
description: Technical reference for Statement AI — configuration, Supabase setup, GDPR controls, and the full API reference.
---
<div class="letterhead">
  <p class="letterhead-eyebrow">
    <span>Statement AI</span>
    <span>Doc. Ref. API-2026</span>
    <span>Self-Hosted REST API</span>
  </p>
  <h1>Documentation</h1>
  <p class="lede">Configuration, Supabase setup, GDPR controls, and the full API reference for running Statement AI yourself.</p>
  <p class="letterhead-crumbs">For installation basics, see the <a href="../README.md">Quickstart in the README</a>.</p>
</div>

<div class="content" markdown="1">

## Features

<table>
<tr>
<td width="50%" valign="top">

**🔐 Security & Access**
- JWT-based authentication (access + refresh tokens)
- Per-user data isolation — every user only ever sees their own statements and transactions
- Authenticated, ownership-checked downloads — original PDFs are never publicly reachable

**🤖 AI Processing**
- Automatic transaction extraction and categorization via Google Gemini
- AI-generated financial summary per statement

</td>
<td width="50%" valign="top">

**📄 Data Management**
- PDF upload with type & size validation
- Full account erasure and configurable data retention (GDPR Art. 17)
- Personal data export as JSON (GDPR Art. 15/20)

**🐳 Operations**
- Fully dockerized (Django + PostgreSQL)
- Automated retention cleanup via cron sidecar

</td>
</tr>
</table>

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Django 4.2 + Django REST Framework |
| **Auth** | `djangorestframework-simplejwt` |
| **Database** | PostgreSQL 15 |
| **AI** | Google Gemini (`gemini-2.5-flash`) |
| **Deployment** | Docker / Docker Compose |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- A [Google Gemini API key](https://aistudio.google.com/apikey)

### Installation

**1. Clone and configure**

```bash
git clone https://github.com/<your-username>/statement-ai.git
cd statement-ai
```

```bash
cp .env.example .env
```

Then fill in your own values in `.env`.

**2. Build and start the containers**

```bash
sudo docker compose up -d --build
```

**3. Run database migrations**

```bash
sudo docker compose exec web python manage.py migrate
```

The API is then available at `http://localhost:8000/api/`.

### Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | `1` for development, `0` for production | `0` |
| `GEMINI_API_KEY` | Your Google Gemini API key | `AI...` |
| `DB_ENGINE` | `local` (default, docker Postgres) or `supabase` | `supabase` |
| `POSTGRES_DB` | Database name (only used if `DB_ENGINE=local`) | `statement_ai_db` |
| `POSTGRES_USER` | Database user (only used if `DB_ENGINE=local`) | `statement_ai_user` |
| `POSTGRES_PASSWORD` | Database password (only used if `DB_ENGINE=local`) | `********` |
| `SUPABASE_DB_HOST` | Supabase Postgres host (only used if `DB_ENGINE=supabase`) — direct or pooler host, see [Using Supabase](#using-supabase-instead-of-the-local-postgres-container) | `db.xxxxxxxxxxxx.supabase.co` |
| `SUPABASE_DB_PORT` | Supabase Postgres port (only used if `DB_ENGINE=supabase`) — `5432` direct, `6543` if using the pooler | `5432` |
| `SUPABASE_DB_NAME` | Supabase database name (only used if `DB_ENGINE=supabase`) | `postgres` |
| `SUPABASE_DB_USER` | Supabase database user (only used if `DB_ENGINE=supabase`) | `postgres` |
| `SUPABASE_DB_PASSWORD` | Supabase database password (only used if `DB_ENGINE=supabase`) | `********` |
| `SUPABASE_DB_SSLMODE` | SSL mode for the Supabase connection (only used if `DB_ENGINE=supabase`); Supabase requires TLS | `require` |
| `ALLOWED_HOSTS` | Comma-separated hosts (production only) | `api.example.com` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins (production only) | `https://app.example.com` |
| `DATA_RETENTION_DAYS` | Days a bank statement is kept before it becomes eligible for automatic deletion | `365` |

> ⚠️ **Warning:** Never commit your `.env` file. Rotate `SECRET_KEY` and `GEMINI_API_KEY` immediately if they are ever exposed.

### Scheduled Data Retention Cleanup

Bank statements older than `DATA_RETENTION_DAYS` are cleaned up automatically by a dedicated `cron` service in `docker-compose.yml`. It runs the same image as `web`, but only executes `manage.py delete_expired_data` on a daily schedule (`cron/statement-ai-cron`, default `03:00`) and otherwise stays idle.

It starts automatically with:

```bash
sudo docker compose up -d --build
```

Check that it's running and inspect its logs with:

```bash
sudo docker compose logs -f cron
```

You can also trigger a cleanup manually at any time — both the `web` and `cron` services share the same code and database:

```bash
sudo docker compose exec cron python manage.py delete_expired_data
```

This permanently deletes every bank statement (and its transactions and PDF file) whose `uploaded_at` is older than the configured retention period. To change the schedule, edit `cron/statement-ai-cron` and rebuild the `cron` service.

> ℹ️ **Note:** If you'd rather not run the sidecar container, remove the `cron` service from `docker-compose.yml` and schedule `docker compose exec web python manage.py delete_expired_data` via the host's system cron instead.

---

## Using Supabase Instead of the Local Postgres Container

Supabase is a hosted **PostgreSQL** database. This project already talks to Postgres via Django's `psycopg2` backend, so pointing it at Supabase is just a matter of changing connection settings:

- No code changes
- No different driver
- No REST API involved

### 1. Create the Supabase Project *(manual, one-time)*

1. Go to [supabase.com](https://supabase.com) → **New project** → pick a name, region, and a database password.
2. Go to **Project Settings → Database → Connection parameters** and note the `Host`, `Port`, `Database name` (`postgres` by default), `User`, and your password.
   - Use the **Session pooler** or **Transaction pooler** host for most deployments — it works better with container restarts and multiple workers.
   - The **direct connection** host also works for a single always-on container like this one.

> ℹ️ **Note:** The Supabase **project** must be created manually in the dashboard — there's no "create project" API call to run from app code. Everything *inside* it (tables, columns, indexes) is created automatically in step 3.

### 2. Configure Environment Variables

Add the following to your `.env`:

```bash
DB_ENGINE=supabase
SUPABASE_DB_HOST=db.xxxxxxxxxxxx.supabase.co   # or the pooler host
SUPABASE_DB_PORT=5432                          # 6543 if using the pooler
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-db-password
SUPABASE_DB_SSLMODE=require
```

### 3. Create the Schema

You do **not** need to create tables manually in the Supabase SQL editor. The existing Django migrations create the exact same schema automatically — `BankStatement`, `Transaction`, plus Django's own `auth_user`, `django_session`, and so on.

**Start the stack**

```bash
docker compose up -d --build
```

With `DB_ENGINE=supabase` set in `.env`, the local `db` service is skipped automatically — it only starts for `DB_ENGINE=local`, so there's no need to name `web`/`cron` explicitly anymore.

**Run migrations**

```bash
docker compose exec web python manage.py migrate
```

**Create an admin user** *(optional, for `/admin`)*

```bash
docker compose exec web python manage.py createsuperuser
```

That's it — zero changes needed to `models.py`, `views.py`, or `serializers.py`.

### How Access Works *(no REST API needed for the database)*

- Django connects to Supabase's Postgres **directly over the Postgres wire protocol** via `psycopg2` (already in `requirements.txt`) — the same way it talks to the local container today. This is the correct way to use Supabase from a Django backend.
- Supabase's REST/GraphQL API (PostgREST) and the `supabase-py` SDK are a *different, optional* layer meant for client-side apps without their own backend. Since Django already **is** the backend and owns the schema via migrations, neither is needed for database access.
- `supabase-py` only becomes relevant if you later want other Supabase services from this backend — for example, Supabase Storage for the PDF files.

### Is Supabase Worth It Here, or Better to Self-Host on GCP/AWS?

Both connect the same way (plain Postgres), so this is an ops/hosting tradeoff, not a code one:

| | **Supabase** | **Self-Hosted Postgres (Cloud SQL / RDS)** |
|---|---|---|
| Setup effort | Minutes, via dashboard | You provision and manage the instance yourself |
| Ops burden | Backups, patching, scaling handled for you | You own backups, patching, HA, monitoring |
| Cost at small scale | Generous free tier | Smallest Cloud SQL/RDS tiers often cost more for the same workload |
| Data residency | Limited region choice, EU regions available | Full control — matters for strict GDPR residency needs |
| Vendor lock-in | Low — vanilla Postgres, portable via `pg_dump`/`pg_restore` | None, but you own the ops |
| Extra features | Auth, Storage, Realtime available if needed later | None built-in |

This project already has its own GDPR/retention logic (`delete_expired_data`), JWT auth, and per-user isolation, and doesn't need Supabase's Auth/Storage/Realtime:

- **Supabase** is the better fit if you want a managed Postgres fast with minimal ops, and might use Supabase Storage for PDFs later.
- **Cloud SQL / RDS** is the better fit if the API itself will run in GCP/AWS anyway (Cloud Run, ECS, etc.) — one cloud account, one network boundary, one bill, tighter region/VPC control.
- Either is **strictly better than the local Docker Postgres** for anything beyond local dev, since that container's data lives only in an unmanaged Docker volume.

> 💡 **Suggestion:** If you're not already committed to GCP/AWS for the rest of the stack, start with Supabase for the fastest path to a properly managed, backed-up Postgres. Since it's plain Postgres underneath, migrating later to Cloud SQL/RDS is a standard `pg_dump`/`pg_restore` — no Django code changes required.

> ✅ **Tip:** All variables in the table above — including `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and the `POSTGRES_*` credentials — are forwarded from `.env` into the `web`, `cron`, and `db` containers via `docker-compose.yml`. Changing a value in `.env` and rebuilding is enough; you don't need to edit `docker-compose.yml` by hand.

---

## Privacy & GDPR

Statement AI processes financial data extracted from bank statements, which is personal data under the GDPR. The following measures are implemented:

| Measure | Implementation |
|---|---|
| 🧹 **Data minimization & retention** | Statements are automatically eligible for deletion after `DATA_RETENTION_DAYS` |
| 🗑️ **Right to erasure** | [`DELETE /api/auth/account/`](#14-delete-my-account) permanently removes the account, statements, transactions & PDFs |
| 📤 **Right of access / portability** | [`GET /api/auth/export/`](#13-export-my-data) returns all personal data as JSON |
| 🔒 **Access control** | PDFs are never publicly reachable, only via the [authenticated download endpoint](#12-download-the-original-pdf) |
| 🌍 **Third-country data transfer** | Statement content is sent to **Google Gemini** (Google LLC, USA) for AI processing |

> 🤖 **Note on Gemini data usage:** This project uses a `GEMINI_API_KEY` from the Gemini API's **paid quota** (i.e. a Cloud project with an active billing account). According to Google's own terms, on Paid Services Google does **not** use your prompts or the PDF/statement content you submit, nor the generated responses, to improve its products or train models; prompts and responses are only logged for a limited time solely to detect and prevent violations of Google's Prohibited Use Policy and for required legal/regulatory disclosures. This is a different (and stricter) data handling regime than the **free/unpaid** Gemini tier, where submitted content and responses *may* be used by Google to improve its products and may be reviewed by humans. If you run this project on the free tier, treat it as unsuitable for real users' financial data. See Google's official **[Gemini API Additional Terms of Service](https://ai.google.dev/gemini-api/terms)**, sections "Paid Services → How Google Uses Your Data" and "Unpaid Services → How Google Uses Your Data", for the authoritative wording.

> ⚖️ **Disclaimer:** This section describes the technical measures available in the API — **not legal advice**. Consult a data protection professional before processing real users' financial data in production. If you operate this API for real users in the EU/EEA, you are responsible for having a valid legal basis and a Data Processing Agreement (DPA) with Google covering this transfer.

---

## API Reference

<div align="center">

**Base URL (local):** `http://localhost:8000/api/` &nbsp;|&nbsp; **Format:** JSON (exception: file upload as `multipart/form-data`) &nbsp;|&nbsp; **Authentication:** JWT (Bearer Token)

</div>

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

Once the access token expires, use the [refresh endpoint](#5-refresh-token) to obtain a new one without logging in again. All endpoints except registration and login require a valid access token — without one, the API responds with `401 Unauthorized`.

### 2. Endpoints Overview

| Method | Path | Auth Required | Description |
|---|---|---|---|
| <span class="pill pill-post">POST</span> | `/api/auth/register/` | No | Register a new user |
| <span class="pill pill-post">POST</span> | `/api/auth/login/` | No | Obtain access & refresh tokens |
| <span class="pill pill-post">POST</span> | `/api/auth/refresh/` | No (refresh token required) | Obtain a new access token |
| <span class="pill pill-delete">DELETE</span> | `/api/auth/account/` | Yes | Permanently delete your account and all associated data |
| <span class="pill pill-get">GET</span> | `/api/auth/export/` | Yes | Export all personal data as JSON |
| <span class="pill pill-get">GET</span> | `/api/statements/` | Yes | List your own bank statements |
| <span class="pill pill-post">POST</span> | `/api/statements/upload/` | Yes | Upload a bank statement (PDF) & process it via AI |
| <span class="pill pill-get">GET</span> | `/api/statements/analytics/` | Yes | AI evaluations of all processed bank statements |
| <span class="pill pill-delete">DELETE</span> | `/api/statements/delete-all/` | Yes | Delete all your own bank statements + transactions |
| <span class="pill pill-delete">DELETE</span> | `/api/statements/<int:pk>/` | Yes | Delete a single bank statement |
| <span class="pill pill-get">GET</span> | `/api/statements/<int:pk>/file/` | Yes | Download the original PDF of a bank statement |
| <span class="pill pill-get">GET</span> | `/api/transactions/` | Yes | List your own transactions |

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
| `category` | string (enum) | One of the 15 categories below |

<div class="chips">
  <span class="chip">Housing &amp; Utilities</span>
  <span class="chip">Groceries &amp; Food</span>
  <span class="chip">Dining Out &amp; Cafes</span>
  <span class="chip">Transportation</span>
  <span class="chip">Shopping &amp; Retail</span>
  <span class="chip">Subscriptions &amp; Media</span>
  <span class="chip">Health &amp; Medical</span>
  <span class="chip">Financial &amp; Insurance</span>
  <span class="chip">Salary &amp; Main Income</span>
  <span class="chip">Secondary Income</span>
  <span class="chip">Transfers &amp; P2P</span>
  <span class="chip">Education &amp; Childcare</span>
  <span class="chip">Travel &amp; Vacations</span>
  <span class="chip">Cash &amp; ATM</span>
  <span class="chip">Miscellaneous &amp; Other</span>
</div>

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

---

## Project Structure

```
statement_ai/
├── statement_ai/                 # Django project
│   ├── settings.py                # Settings, incl. local/Supabase DB switch & global exception handler
│   ├── urls.py                    # Root URL config (includes statements/urls.py under /api/)
│   └── wsgi.py                    # WSGI entrypoint
├── statements/                   # Main app
│   ├── models.py                  # BankStatement & Transaction models
│   ├── serializers.py             # DRF serializers
│   ├── services.py                # Gemini AI integration (extraction, categorization, evaluation)
│   ├── views.py                   # API views
│   ├── urls.py                    # App-level routes
│   ├── exceptions.py              # Project-wide DRF exception handler (consistent JSON errors)
│   ├── management/
│   │   └── commands/
│   │       └── delete_expired_data.py   # GDPR retention cleanup command
│   └── migrations/
│       ├── 0001_initial.py
│       └── 0002_transaction_payee_payer_and_more.py
├── cron/
│   ├── entrypoint.sh              # Cron sidecar entrypoint
│   └── statement-ai-cron          # Crontab: daily retention cleanup schedule
├── .github/
│   └── workflows/
│       └── codacy.yml             # Codacy security scan CI workflow
├── manage.py                     # Django management CLI
├── .env.example                   # Template for required environment variables
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── LICENSE                        # MIT License
└── requirements.txt
```
-e 
</div>
