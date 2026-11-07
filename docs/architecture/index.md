---
layout: page
title: Architecture
permalink: /architecture/
---

# Architecture

Statement AI is a single Django application with a Celery worker beside it. This page explains the components, how a request travels through the code, the data model, and the main workflows end to end.

## Components

| Component | Role |
| --- | --- |
| `web` | Django and Django REST Framework. Serves `/api/` and `/admin/`, validates input, authenticates JWTs, stores files and rows, and queues processing jobs. |
| `worker` | A Celery worker that runs `process_statement_task`. It calls Gemini and writes the results. Two worker processes by default. |
| `redis` | Message broker for Celery (database `0`) and Django cache (database `1`). The cache holds rate-limit and failed-login counters. |
| `db` or Supabase | PostgreSQL. Stores users, statements, transactions, usage records, audit events and 2FA data. |
| `cron` | The same image as `web`. Runs `manage.py delete_expired_data` every day at 03:00 UTC. |
| `media_data` volume | Uploaded PDFs under `statements/YYYY/MM/`. Shared by `web`, `worker` and `cron`. |
| Google Gemini | Receives the PDF and returns structured JSON. |

```text
                          +----------------------------------------------+
                          |               Docker Compose                 |
                          |                                              |
 API client --HTTP/JSON-->|  web (Django + DRF) ---- rows ----> PostgreSQL
                          |    |   |                               ^  ^
                          |    |   +---- PDF files ---> media      |  |
                          |    |                         ^         |  |
                          |    +--- enqueue --> Redis    |         |  |
                          |         (also rate limits)   |         |  |
                          |              |               |         |  |
                          |              v               |         |  |
                          |         worker (Celery) -----+---------+  |
                          |              |   ^                        |
                          |              |   | JSON                   |
                          |              v   |                        |
                          |         Google Gemini API                 |
                          |                                           |
                          |  cron (delete_expired_data) --------------+
                          +----------------------------------------------+
```

The Django project is `statement_ai/`. All application code is in one app, `statements/`. There is no separate service layer beyond `services.py` (the Gemini call) and `tasks.py` (the Celery task).

## Request pipeline

Every request under `/api/` passes two custom middlewares before it reaches a view:

1. `APIUsageTrackingMiddleware` stores one `APIUsageRecord` per request unless tracking is disabled.
2. `APIRateLimitMiddleware` applies the global limit and the per-endpoint limit, and answers `429` before any view code runs.

Authentication is `SecurityVersionJWTAuthentication`, an extension of SimpleJWT that also compares the token's `auth_version` with the user's current value. Every view requires authentication by default, and the public endpoints opt out explicitly. A project-wide exception handler in `statements/exceptions.py` shapes error responses; see the [API reference]({{ '/api-reference/#errors' | relative_url }}).

## Data model

| Model | Purpose |
| --- | --- |
| `BankStatement` | One uploaded PDF: owner, file, `uploaded_at`, `processing_status`, `processing_error`, `is_processed`, `ai_evaluation`. |
| `Transaction` | One extracted transaction, belonging to a statement and deleted with it. |
| `APIUsageRecord` | One row per API request: route, method, status code, duration, request size. |
| `GeminiUsageRecord` | One row per Gemini call: model, success or failure, token counts, duration, error class. |
| `AuditEvent` | Security and data-change events with actor, target, outcome and details. |
| `UserSecuritySettings` | Per-user 2FA flag, encrypted TOTP secrets, last used TOTP counter and `auth_version`. |
| `TwoFactorRecoveryCode` | Hashed recovery codes with a used timestamp. |
| `TwoFactorLoginChallenge` | Hashed one-time login challenges with expiry and a failed-attempt counter. |

Migrations are in `statements/migrations/`, `0001` to `0007` at the time of writing. Usage records and audit events keep their rows when a user is deleted; the user reference is set to null.

Two details about `Transaction`: `transaction_type` has Django `choices`, but those are not enforced by the database, and `category` is a plain text field (maximum 60 characters, default `Uncategorized`). Both lists live in the Gemini prompt.

## Technology

| Layer | Technology |
| --- | --- |
| Framework | Django 4.2, Django REST Framework |
| Authentication | `djangorestframework-simplejwt`, `pyotp`, `cryptography` (Fernet) |
| Background jobs | Celery 5.4 with Redis |
| Cache | `django-redis`, with an in-process fallback in development |
| Database | PostgreSQL 15 through `psycopg2-binary` |
| AI | Google Gemini through the `google-genai` SDK |
| Cross-origin requests | `django-cors-headers` |
| Runtime | Python 3.11, Docker, Docker Compose |

## Core workflows

### Sign up and log in

```text
Client                         API                          Email
  | POST /auth/register/        |                             |
  |---------------------------->| link with uid + token ----->|
  |<-- 201 (account inactive) --|                             |
  | POST /auth/register/confirm/|                             |
  |---------------------------->|                             |
  |<-- 200 (account active) ----|                             |
  | POST /auth/login/           |                             |
  |---------------------------->|                             |
  |<-- access + refresh --------|   (no 2FA)                  |
  |<-- mfa_required + challenge-|   (2FA enabled)             |
  | POST /auth/login/2fa/       |                             |
  |---------------------------->|                             |
  |<-- access + refresh --------|                             |
```

Send the access token on every request. When it expires, call `/auth/refresh/`. When the refresh token expires after a day, log in again.

To add 2FA to an existing account: call `/auth/2fa/setup/` with the password, add the secret to an authenticator app, call `/auth/2fa/enable/` with the first code, and store the recovery codes. Log in again afterwards.

### Statement processing

```text
Client            web                Redis        worker            Gemini      PostgreSQL
  | POST upload    |                   |             |                 |             |
  |--------------->| validate; create statement (pending) ----------------------->  |
  |                | enqueue (after the DB commit) -->|                 |             |
  |<-- 202 + status_url                |             |                 |             |
  |                |                   |-- deliver ->| status=processing ------->    |
  |                |                   |             |-- PDF + prompt->|             |
  |                |                   |             |<---- JSON ------|             |
  |                |                   |             | replace transactions, save evaluation
  |                |                   |             | status=completed ---------->  |
  | GET status ... |  (repeat until completed or failed)                            |
```

Step by step:

1. **Validation.** The API checks content type, file signature and size. If `GEMINI_MONTHLY_LIMIT_PER_USER` is set, it counts the user's statements this month while holding a row lock on the user, so concurrent uploads cannot slip past the cap.
2. **Storage and queueing.** The file is saved, a `BankStatement` row is created as `pending`, and the Celery task is queued only after the database transaction commits. If queueing fails, the statement is marked `failed` and the client gets a `503`.
3. **Extraction.** The worker sets the status to `processing`, reads the PDF and sends the raw bytes to Gemini with the prompt. There is no local PDF parsing or OCR.
4. **Parsing and storage.** Any Markdown code fence around the reply is removed and the text is parsed as JSON. In one database transaction, the statement's existing transactions are deleted and the new ones are inserted, and the evaluation is saved.
5. **Completion.** The status becomes `completed`.
6. **Failure.** Any exception (Gemini error, invalid JSON, database error) triggers a retry with exponential backoff and jitter, up to three times. After the last retry the status becomes `failed` with a generic message. A job for a statement that is already `completed` exits immediately. Every Gemini call, successful or not, is recorded in `GeminiUsageRecord` when tracking is on, so a statement that needed retries has several records.

Jobs are acknowledged late and rejected on worker loss, so a job whose worker dies is redelivered.

### Reading the data

Once a statement is `completed`, use `GET /api/transactions/` with filters, `GET /api/statements/<id>/` for one statement with its transactions, or `GET /api/statements/analytics/` for the AI summaries.

### Managing your data

`GET /api/auth/export/` returns a JSON copy of the account's data. `GET /api/statements/<id>/file/` returns the original PDF. `DELETE /api/statements/<id>/` and `/api/statements/delete-all/` remove statements, and `DELETE /api/auth/account/` removes everything. Independently of what users do, the cleanup job removes statements after `DATA_RETENTION_DAYS`.

## Related pages

- [Features]({{ '/features/' | relative_url }})
- [API reference]({{ '/api-reference/' | relative_url }})
- [Security]({{ '/security/' | relative_url }})
- [Deployment]({{ '/deployment/' | relative_url }})
