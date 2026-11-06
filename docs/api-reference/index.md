---
layout: page
title: API Reference
permalink: /api-reference/
---

# API Reference

This documentation reflects the current Django REST API in this repository. The local service runs on `http://localhost:8001/api/` by default when started with Docker Compose.

## Base URL and format

- Base URL: `http://localhost:8001/api/`
- Format: JSON for most endpoints
- File upload: `multipart/form-data`
- Authentication: JWT bearer token

## Authentication

The application uses `djangorestframework-simplejwt` for authentication. After a successful login, the API returns an `access` token and a `refresh` token.

Send the `access` token in the `Authorization` header for every protected request:

```http
Authorization: Bearer <access_token>
```

The default token lifetimes are:

| Token | Lifetime |
| --- | --- |
| Access token | 60 minutes |
| Refresh token | 1 day |

If the access token expires, use `POST /api/auth/refresh/` to create a new access token.

## Rate limits

Requests that exceed a limit receive `429 Too Many Requests` with an `error` field and a `Retry-After` header. API and endpoint quotas use fixed windows; the failed-login cooldown expires 15 minutes after the first failure for that IP address and username.

| Request | Limit |
| --- | --- |
| Anonymous API request | 60 per minute per IP address |
| Authenticated API request | 120 per minute per user |
| `POST /api/auth/register/` | 5 per hour per IP address |
| `POST /api/auth/login/` | 10 per minute per IP address |
| `POST /api/auth/password-reset/` | 5 per hour per IP address |
| Password reset email address | 3 per hour per normalized email address |
| `POST /api/auth/password-reset/confirm/` | 10 per hour per IP address |
| Failed logins | 5 per 15 minutes per IP address and username |
| `POST /api/statements/upload/` | 5 per hour per user |

## Endpoint overview

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register/` | No | Create a new user |
| `POST` | `/api/auth/login/` | No | Log in and receive JWT tokens |
| `POST` | `/api/auth/password-reset/` | No | Request password reset instructions |
| `POST` | `/api/auth/password-reset/confirm/` | No | Set a new password with a reset token |
| `POST` | `/api/auth/refresh/` | No | Refresh an expired access token |
| `DELETE` | `/api/auth/account/` | Yes | Delete the authenticated user's account |
| `GET` | `/api/auth/export/` | Yes | Export all personal data for the user |
| `GET` | `/api/statements/` | Yes | List the logged-in user's statements |
| `POST` | `/api/statements/upload/` | Yes | Upload and process a PDF statement |
| `GET` | `/api/statements/<id>/` | Yes | Retrieve a statement and its transactions |
| `DELETE` | `/api/statements/<id>/` | Yes | Delete one statement and its file |
| `GET` | `/api/statements/<id>/file/` | Yes | Download the original uploaded PDF |
| `DELETE` | `/api/statements/delete-all/` | Yes | Delete every statement belonging to the user |
| `GET` | `/api/statements/analytics/` | Yes | Return AI evaluations for processed statements |
| `GET` | `/api/transactions/` | Yes | List the user's transactions |
| `GET` | `/api/transactions/<id>/` | Yes | Retrieve one transaction |
| `GET` | `/api/analytics/` | Yes | Compatibility alias for analytics |

## Auth flows

### Register a user

```http
POST /api/auth/register/
Content-Type: application/json
```

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "StrongPass123!"
}
```

Response:

```json
{
  "username": "alice",
  "email": "alice@example.com"
}
```

Registration is limited to five requests per hour per IP address. Requests above this limit receive `429 Too Many Requests` until the limit window resets.

Passwords must be at least 12 characters long and pass Django's checks for common passwords, similarity to account details, and all-numeric values. Passphrases are accepted; a specific mix of character types is not required.

### Log in

```http
POST /api/auth/login/
Content-Type: application/json
```

```json
{
  "username": "alice",
  "password": "StrongPass123!"
}
```

Response:

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

### Refresh a token

```http
POST /api/auth/refresh/
Content-Type: application/json
```

```json
{
  "refresh": "<refresh_token>"
}
```

Response:

```json
{
  "access": "<new_access_token>"
}
```

### Request a password reset

```http
POST /api/auth/password-reset/
Content-Type: application/json
```

```json
{
  "email": "alice@example.com"
}
```

The API always returns the same `200 OK` message, whether or not an active account uses the address. If exactly one active account matches, the email contains a one-time token and a link to the configured client reset page. The client should read `uid` and `token` from the URL fragment and remove the fragment from the address bar before loading third-party resources.

### Confirm a password reset

```http
POST /api/auth/password-reset/confirm/
Content-Type: application/json
```

```json
{
  "uid": "MQ",
  "token": "<one_time_token>",
  "new_password": "A-long-passphrase-2026"
}
```

The token expires after one hour by default, can be used once, and is invalidated as soon as the password changes. A successful reset revokes existing access and refresh tokens. Invalid or expired links and passwords that fail the password checks receive `400 Bad Request`.

## Notes on permissions

All endpoints except registration, login, and token refresh are protected by the default authentication class. A request without a valid token returns `401 Unauthorized`.

## Related pages

- [Statement endpoints](./statements.html)
- [Transaction endpoints](./transactions.html)
- [Account and privacy endpoints](./account.html)
- [Installation guide](../installation/)
- [Security overview](../security/)
