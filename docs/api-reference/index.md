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

## Endpoint overview

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register/` | No | Create a new user |
| `POST` | `/api/auth/login/` | No | Log in and receive JWT tokens |
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

## Notes on permissions

All endpoints except registration, login, and token refresh are protected by the default authentication class. A request without a valid token returns `401 Unauthorized`.

## Related pages

- [Statement endpoints](./statements.html)
- [Transaction endpoints](./transactions.html)
- [Account and privacy endpoints](./account.html)
- [Installation guide](../installation/)
- [Security overview](../security/)
