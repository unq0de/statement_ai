---
layout: page
title: API Reference
permalink: /api-reference/
---

# API Reference

This reference describes the REST API as implemented in this repository. The repository has no OpenAPI or Swagger specification, so these pages are the reference. The detailed endpoint descriptions are split across four pages:

- [Authentication endpoints]({{ '/api-reference/authentication/' | relative_url }}): registration, login, 2FA, token refresh, password reset
- [Statement endpoints]({{ '/api-reference/statements/' | relative_url }}): upload, status, list, download, delete, analytics
- [Transaction endpoints]({{ '/api-reference/transactions/' | relative_url }}): list, filter and read transactions
- [Account and privacy endpoints]({{ '/api-reference/account/' | relative_url }}): data export and account deletion

This page covers what applies everywhere: base URL, authentication, conventions, error formats, status codes and the endpoint overview.

## Base URL and format

- Base URL with Docker Compose: `http://localhost:8001/api/`
- Format: JSON, except the upload endpoint, which uses `multipart/form-data`
- Authentication: JWT bearer token
- Versioning: none. All routes are unversioned.

## Authentication

The API uses `djangorestframework-simplejwt`. A successful login returns an `access` and a `refresh` token. Send the access token on every protected request:

```http
Authorization: Bearer <access_token>
```

| Token | Lifetime |
| --- | --- |
| Access token | 60 minutes |
| Refresh token | 1 day |

When the access token expires, call `POST /api/auth/refresh/`. Tokens stop working earlier if the user changes or resets the password, or enables or disables two-factor authentication. A request without a valid token to a protected endpoint returns `401 Unauthorized`.

## Conventions

**Ownership.** Statements and transactions are always filtered to the authenticated user. Requesting another user's resource returns `404`, exactly like a missing one.

**Pagination.** There is none. List endpoints return a plain JSON array with everything that matches.

**Amounts.** `amount` is a decimal serialized as a string with two decimal places, for example `"-65.40"`.

**Methods.** Other HTTP methods on the routes below return `405 Method Not Allowed`. There are no endpoints to create, edit or delete individual transactions.

## Errors

Errors have several shapes, depending on where they originate:

| Source | Shape | Example |
| --- | --- | --- |
| Statement AI views and rate limiting | `{"error": "message"}` | `{"error": "Rate limit exceeded."}` |
| DRF authentication and permission checks | `{"detail": "message"}` | `{"detail": "Authentication credentials were not provided."}` |
| SimpleJWT token errors | `{"detail": "...", "code": "token_not_valid", "messages": [...]}` | |
| Serializer validation | field name mapped to a list of messages | `{"password": ["This password is too common."]}` |
| Unexpected exceptions | `{"error": "An unexpected server error occurred."}` with status `500` | |

A project-wide exception handler (`statements/exceptions.py`) converts DRF throttling errors to the `{"error": ...}` shape, and turns an unhandled "object does not exist" error, for example a token for a deleted user, into `401` with `{"error": "Invalid or expired token."}`. Any other unhandled exception is logged with its traceback and returned as the generic `500` message, without internal details.

## Status codes

| Status | Meaning |
| --- | --- |
| `200` | Success |
| `201` | Account created |
| `202` | Statement accepted for background processing |
| `400` | Validation failed or input was rejected |
| `401` | Missing, invalid, expired or revoked token; wrong credentials |
| `404` | Not found, not yours, or the feature is unavailable (2FA turned off) |
| `405` | Method not allowed on this route |
| `409` | Conflict: 2FA is already enabled |
| `429` | A rate limit or the monthly processing limit was reached. The response has a `Retry-After` header. |
| `500` | Unexpected server error |
| `503` | An upload could not be stored or queued; or `/health/` found an unreachable dependency |

## Rate limits

Requests over a limit receive `429 Too Many Requests`, an `error` field and a `Retry-After` header in seconds. Quotas use fixed windows. The full table, including per-endpoint limits and the failed-login cooldown, is on the [Configuration]({{ '/configuration/#rate-limits' | relative_url }}) page.

## Endpoint overview

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register/` | No | Create an inactive account and send a confirmation email |
| `POST` | `/api/auth/register/confirm/` | No | Activate an account |
| `POST` | `/api/auth/register/resend-confirmation/` | No | Resend the confirmation email |
| `POST` | `/api/auth/login/` | No | Log in and receive tokens, or a 2FA challenge |
| `POST` | `/api/auth/login/2fa/` | No | Complete a 2FA login with a TOTP or recovery code |
| `POST` | `/api/auth/refresh/` | No | Get a new access token from a refresh token |
| `POST` | `/api/auth/password-reset/` | No | Request a password reset email |
| `POST` | `/api/auth/password-reset/confirm/` | No | Set a new password with a reset token |
| `GET` | `/api/auth/2fa/` | Yes | Check 2FA status |
| `POST` | `/api/auth/2fa/setup/` | Yes | Start TOTP enrollment |
| `POST` | `/api/auth/2fa/enable/` | Yes | Confirm enrollment with a code |
| `POST` | `/api/auth/2fa/disable/` | Yes | Turn 2FA off |
| `POST` | `/api/auth/2fa/recovery-codes/` | Yes | Replace the recovery codes |
| `GET` | `/api/auth/export/` | Yes | Export personal data as JSON |
| `DELETE` | `/api/auth/account/` | Yes | Delete the account and all its data |
| `POST` | `/api/statements/upload/` | Yes | Upload a PDF and queue it for processing |
| `GET` | `/api/statements/` | Yes | List statements with their transactions |
| `GET` | `/api/statements/<id>/` | Yes | Retrieve one statement |
| `GET` | `/api/statements/<id>/status/` | Yes | Check processing status |
| `GET` | `/api/statements/<id>/file/` | Yes | Download the original PDF |
| `DELETE` | `/api/statements/<id>/` | Yes | Delete one statement |
| `DELETE` | `/api/statements/delete-all/` | Yes | Delete all of the user's statements |
| `GET` | `/api/statements/analytics/` | Yes | AI evaluations of processed statements |
| `GET` | `/api/analytics/` | Yes | Alias of the analytics endpoint |
| `GET` | `/api/transactions/` | Yes | List, filter and search transactions |
| `GET` | `/api/transactions/<id>/` | Yes | Retrieve one transaction |
| `GET` | `/health/` | No | Health probe for the database and cache. Outside `/api/`, so no authentication, rate limits or usage tracking. `200` when healthy, `503` otherwise |

## Related pages

- [Getting started]({{ '/getting-started/' | relative_url }})
- [Architecture]({{ '/architecture/' | relative_url }})
- [Security]({{ '/security/' | relative_url }})
