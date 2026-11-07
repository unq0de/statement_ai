---
layout: page
title: Features
permalink: /features/
---

# Features

This page describes what the current code does, area by area. For the exact request and response formats, see the [API reference]({{ '/api-reference/' | relative_url }}). For how the pieces fit together, see [Architecture]({{ '/architecture/' | relative_url }}).

## Accounts and registration

The API uses Django's default user model. A user registers with a username, email address and password. The new account is inactive: it cannot log in until the one-time link in the confirmation email has been used. The link points to a page of your own client application (`REGISTRATION_CONFIRMATION_URL`) and carries `uid` and `token` in the URL fragment, which browsers do not send in HTTP requests. The client reads them and posts them to the confirm endpoint. Links are valid for one hour by default and can be used once.

If the email never arrives, a resend endpoint issues a new link. It answers identically whether or not an unconfirmed account exists for the address, so it cannot be used to find out who is registered. If sending the email fails, the failure is logged but the client still gets a success response.

## Login and tokens

Login exchanges username and password for an `access` token (60 minutes) and a `refresh` token (1 day). The refresh endpoint returns a new access token and does not rotate the refresh token.

Tokens can be revoked in two ways. They carry a hash of the user's password, so a password change or reset invalidates every token the user holds. They also carry an `auth_version` number that is increased when two-factor authentication is enabled or disabled, which invalidates older tokens as well.

Accounts whose correct password no longer satisfies the current password policy are refused tokens and told to reset it. This applies a tightened policy to existing accounts without a migration, and such an attempt is not counted as a failed login.

## Password policy

The policy is configurable through environment variables: minimum length (12 by default), similarity to username or email, common passwords, all-numeric passwords, and a requirement for at least one punctuation mark or symbol. There is no required mix of upper-case, lower-case and digits, so long passphrases work. See [Configuration]({{ '/configuration/' | relative_url }}) for the variable names.

## Password reset

A reset request always returns the same message, whether or not an active account uses the address. If exactly one active account matches, an email with a reset link is sent to `PASSWORD_RESET_URL`. The client sends `uid`, `token` and the new password to the confirm endpoint. The new password is checked against the policy, the token is single-use, and a successful reset invalidates all existing tokens. If `PASSWORD_RESET_URL` is empty, the email contains the `uid` and `token` values directly instead of a link.

## Optional two-factor authentication

Users can protect their account with a TOTP authenticator app. Enrollment has three steps:

1. `POST /api/auth/2fa/setup/` with the password returns a secret and an `otpauth_url`. The client shows the URL as a QR code or the secret as text. The secret is pending and valid for twice the challenge timeout (10 minutes by default).
2. The user adds it to an authenticator app.
3. `POST /api/auth/2fa/enable/` with a first six-digit code activates 2FA and returns the recovery codes (10 by default). They are shown only this once; the server stores hashes.

From then on, a correct username and password do not return tokens. They return a short-lived, single-use challenge. The client completes the login with either a current TOTP code or an unused recovery code. A TOTP code is accepted within one 30-second step either side of the current one and can only be used once. A challenge is burned after `TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS` wrong codes.

TOTP secrets are encrypted with a Fernet key. Disabling 2FA and regenerating recovery codes require both the password and a current TOTP code. Enabling or disabling 2FA signs the user out everywhere, so log in again afterwards. If `TWO_FACTOR_ENABLED=0`, the whole feature is off and its endpoints return `404`. The API does not render QR codes; that is up to the client.

## Statement upload

An authenticated user uploads a PDF to `POST /api/statements/upload/` as `multipart/form-data`. The field is called `file`; `document` is accepted as an alternative. The API checks, in this order:

1. A file part is present.
2. The declared content type is `application/pdf`, `application/octet-stream` or `binary/octet-stream`.
3. The content looks like a PDF. It starts with `%PDF`, or the filename ends in `.pdf` and `%PDF` appears in the first 2 KB. Empty files fail.
4. The size is at most 10 MB.

A passing file is saved under `media/statements/YYYY/MM/`, a `BankStatement` row is created with status `pending`, and a background job is queued. The response is `202 Accepted` with the statement ID and a status URL.

Uploads are limited to 5 per hour per user. An optional monthly cap, `GEMINI_MONTHLY_LIMIT_PER_USER`, limits how many statements one account can submit per calendar month. It counts the user's existing statements, whatever their status, so deleting one frees up quota. The cap is off by default and is meant to put a ceiling on Gemini costs.

## Background processing and status

Extraction runs in a Celery worker, so a slow Gemini call never blocks an HTTP request. A statement moves through four states:

| Status | Meaning |
| --- | --- |
| `pending` | Accepted and queued. |
| `processing` | A worker is working on it. The status stays here between automatic retries. |
| `completed` | Transactions and evaluation are stored. |
| `failed` | Processing gave up, or the job could not be queued. |

Clients poll `GET /api/statements/<id>/status/`. If a job fails, it is retried up to three times with exponential backoff and jitter before the status becomes `failed`. Each attempt replaces the statement's transactions, so a retry cannot leave duplicates behind. If the worker dies mid-job, the job is delivered again rather than lost. The status response contains only a generic error message; the real exception is in the worker log and in the Gemini usage record. There is no endpoint to re-run a failed statement. Upload the file again.

## AI extraction and categorization

The worker sends the raw PDF and a prompt to Gemini. The prompt fixes:

- English output, regardless of the language of the PDF
- the fifteen allowed categories and eight allowed transaction types
- the JSON structure of the answer
- negative amounts for outgoing payments and positive amounts for incoming ones
- an evaluation of at most three sentences, written to the user as "you"

The reply is parsed as JSON and stored: the transactions replace any existing ones for that statement, and the evaluation is saved. Missing fields get defaults (type `FEE_CHARGE`, category `Miscellaneous & Other`, empty payee and description, amount `0`). The code does not check that Gemini's category and type values are on the allowed lists, so treat the lists as strongly expected rather than guaranteed. A transaction without a usable date makes the whole attempt fail.

The model is `gemini-3.5-flash-lite`, set in `statements/services.py`.

## Transactions

Transactions are read-only. `GET /api/transactions/` returns all of the user's transactions across statements and supports these query parameters:

- `statement_id` to restrict the list to one statement
- `category` for a case-insensitive exact match
- `q` for a case-insensitive substring search over description, payee or payer, and category
- `ordering` with `date`, `-date`, `amount` or `-amount` (default `-date`)

`GET /api/transactions/<id>/` returns one transaction. Statements also return their transactions nested. There is no pagination; lists return everything that matches.

## Statement management and analytics

Users can list statements (filter by `processed`, sort by `uploaded_at`), fetch one with its transactions, download the original PDF, delete one statement, or delete all of them. Deleting removes the transactions and the stored PDF as well.

`GET /api/statements/analytics/`, also reachable at `/api/analytics/`, returns the AI evaluation of every processed statement. It does not compute totals or averages.

## Privacy tools

- `GET /api/auth/export/` returns the user's profile and all statements with their transactions as JSON, with a download URL for each PDF.
- `DELETE /api/auth/account/` deletes the user, all statements and transactions, and the stored PDFs. It requires the account password.
- The nightly cleanup deletes statements older than `DATA_RETENTION_DAYS` and prunes the usage and audit tables. Details are on the [Security]({{ '/security/#retention-and-erasure' | relative_url }}) page.

## Abuse protection

A middleware layer rate-limits requests per IP address or per user, with stricter limits on registration, login, password reset, 2FA and upload. Repeated failed logins for the same IP address and username trigger a 15-minute cooldown. The full table is on the [Configuration]({{ '/configuration/#rate-limits' | relative_url }}) page.

## Operator tools

Three Django admin views, all read-only, help operators:

- **API usage records**: route, method, status code, duration and request size. No request bodies, query strings or IP addresses are stored.
- **Gemini usage records**: model, success or failure, token counts, duration and the error class name.
- **Audit events**: security and data-changing actions such as logins, 2FA changes, uploads, processing outcomes, downloads, exports and deletions.

Usage tracking can be switched off with `API_USAGE_TRACKING_ENABLED=0`. Each table has its own retention period.

## Related pages

- [Getting started]({{ '/getting-started/' | relative_url }})
- [Architecture]({{ '/architecture/' | relative_url }})
- [API reference]({{ '/api-reference/' | relative_url }})
- [Security]({{ '/security/' | relative_url }})
