---
title: API Reference — Overview & Authentication
permalink: /api-reference/
---

# API Reference
{: #api-reference }

**Base URL (local):** `http://localhost:8000/api/` &nbsp;|&nbsp; **Format:** JSON (exception: file upload as `multipart/form-data`) &nbsp;|&nbsp; **Authentication:** JWT (Bearer Token)

## Authentication
{: #authentication }

The API uses **JWT (JSON Web Tokens)** via [`djangorestframework-simplejwt`](https://django-rest-framework-simplejwt.readthedocs.io/).

After logging in, you receive an `access` and a `refresh` token. Send the `access` token with **every** request to a protected endpoint in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

| Token | Validity |
|---|---|
| Access Token | 60 minutes |
| Refresh Token | 1 day |

Once the access token expires, use the [refresh endpoint](#refresh-token) to obtain a new one without logging in again. All endpoints except registration and login require a valid access token — without one, the API responds with `401 Unauthorized`.

## Endpoints Overview
{: #endpoints-overview }

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

See [Bank Statements]({{ '/api-reference/statements/' | relative_url }}) and [Transactions]({{ '/api-reference/transactions/' | relative_url }}) for the statement/transaction endpoints, and [Account & Personal Data]({{ '/api-reference/account/' | relative_url }}) for export/erasure.

## Register a User
{: #register-a-user }

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

## Login (Obtain Token)
{: #login-obtain-token }

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

## Refresh Token
{: #refresh-token }

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

---

Next: [Bank Statements]({{ '/api-reference/statements/' | relative_url }}) covers upload, listing, download, and deletion.
