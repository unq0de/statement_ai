---
layout: page
title: Authentication Endpoints
permalink: /api-reference/authentication/
---

# Authentication endpoints

These endpoints cover registration, login, two-factor authentication, token refresh and password reset. Shared conventions, error formats and status codes are on the [API overview]({{ '/api-reference/' | relative_url }}).

## Register

```http
POST /api/auth/register/
Content-Type: application/json
```

No authentication required. Creates an inactive account and emails a confirmation link.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `username` | string | Yes | Must be unique. |
| `email` | string | Yes | Must be a valid address. |
| `password` | string | Yes | Must satisfy the password policy. |

```bash
curl -X POST http://localhost:8001/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"StrongPass123!"}'
```

`201 Created`:

```json
{
  "username": "alice",
  "email": "alice@example.com"
}
```

Errors: `400` with field errors for a taken username, a rejected password or a missing field, and `429` after five registrations per hour from one IP address.

```json
{ "password": ["This password is too common."] }
```

The password policy is configurable; by default it requires 12 characters, rejects common, all-numeric and username-like passwords, and requires one punctuation mark or symbol. See [Configuration]({{ '/configuration/' | relative_url }}).

The email contains a link to `REGISTRATION_CONFIRMATION_URL` with `uid` and `token` in the URL fragment, for example `https://app.example.com/confirm-email/#uid=MQ&token=...`. If sending fails, the failure is logged and the response is still `201`; the user can ask for a new email with the resend endpoint.

## Confirm registration

```http
POST /api/auth/register/confirm/
Content-Type: application/json
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `uid` | string | Yes | From the email link. |
| `token` | string | Yes | From the email link. |

```json
{ "uid": "MQ", "token": "<one_time_token>" }
```

`200 OK`:

```json
{ "message": "Your email address has been confirmed. You can now log in." }
```

`400` for an invalid, expired or already used link. The body is either `{"token": ["This email confirmation link is invalid or expired."]}` or `{"error": "This email confirmation link is invalid or expired."}`. Links are valid for `PASSWORD_RESET_TIMEOUT` seconds (one hour by default).

## Resend the confirmation email

```http
POST /api/auth/register/resend-confirmation/
Content-Type: application/json
```

Body: `{"email": "alice@example.com"}`. Always returns `200 OK` with `{"message": "If an unconfirmed account uses that email, a confirmation email has been sent."}`, whether or not a matching inactive account exists. Limited to 3 emails per hour per address and 10 requests per hour per IP address.

## Log in

```http
POST /api/auth/login/
Content-Type: application/json
```

```json
{ "username": "alice", "password": "StrongPass123!" }
```

`200 OK`:

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

If the account has two-factor authentication enabled, no tokens are issued. The response is a challenge instead:

```json
{
  "mfa_required": true,
  "challenge": "<one_time_challenge>",
  "expires_in": 300
}
```

| Status | Cause |
| --- | --- |
| `401` | Wrong credentials, or the account has not been confirmed yet. |
| `401` | The password is correct but no longer meets the current policy. The message tells the user to request a password reset. This does not count as a failed attempt. |
| `429` | The login rate limit, or the failed-attempt cooldown (5 failures per IP address and username, then 15 minutes). A successful login resets the counter. |

## Complete a 2FA login

```http
POST /api/auth/login/2fa/
Content-Type: application/json
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `challenge` | string | Yes | From the login response. |
| `code` | string | One of | Six-digit TOTP code. |
| `recovery_code` | string | One of | A recovery code such as `A1B2C3D4-E5F6A7B8`. Works once. |

Send exactly one of `code` or `recovery_code`; sending both or neither returns `400`.

```json
{ "challenge": "<one_time_challenge>", "code": "123456" }
```

`200 OK` returns `{"refresh": "...", "access": "..."}`.

`401` with `{"error": "Invalid or expired two-factor challenge."}` covers an unknown, expired, used or exhausted challenge as well as a wrong code. After `TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS` wrong codes the challenge is burned and the user must log in again. `404` if `TWO_FACTOR_ENABLED=0`.

## Refresh a token

```http
POST /api/auth/refresh/
Content-Type: application/json
```

```json
{ "refresh": "<refresh_token>" }
```

`200 OK` returns `{"access": "<new_access_token>"}`. The refresh token is not rotated. `401` if the token is expired or malformed, belongs to an inactive or deleted user, was issued before a password change, or predates a 2FA enable or disable.

## Request a password reset

```http
POST /api/auth/password-reset/
Content-Type: application/json
```

Body: `{"email": "alice@example.com"}`. Always returns `200 OK` with `{"message": "If an active account uses that email, reset instructions have been sent."}`.

An email is sent only if exactly one active account uses the address. It contains a link to `PASSWORD_RESET_URL` with `uid` and `token` in the URL fragment. The client should read them and remove the fragment from the address bar before loading third-party resources. If `PASSWORD_RESET_URL` is empty, the email contains the `uid` and `token` values directly. Limits: 5 requests per hour per IP address and 3 emails per hour per address.

## Confirm a password reset

```http
POST /api/auth/password-reset/confirm/
Content-Type: application/json
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `uid` | string | Yes | From the email. |
| `token` | string | Yes | From the email. |
| `new_password` | string | Yes | Checked against the password policy. |

`200 OK`: `{"message": "Your password has been reset. Please log in again."}`.

`400` for an invalid or expired link, or a password that fails validation (`{"new_password": [...]}`). The token expires after one hour by default and works once. A successful reset invalidates all existing access and refresh tokens.

## Two-factor status

```http
GET /api/auth/2fa/
Authorization: Bearer <access_token>
```

```json
{ "enabled": false, "recovery_codes_remaining": 0 }
```

## Start 2FA setup

```http
POST /api/auth/2fa/setup/
Authorization: Bearer <access_token>
Content-Type: application/json
```

Body: `{"password": "StrongPass123!"}`.

`200 OK`:

```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "otpauth_url": "otpauth://totp/Statement%20AI:alice%40example.com?secret=JBSWY3DPEHPK3PXP&issuer=Statement%20AI",
  "expires_in": 600
}
```

The secret is pending for `expires_in` seconds, which is twice the challenge timeout. The client can render `otpauth_url` as a QR code. Errors: `400` for a wrong password, `409` if 2FA is already enabled, `404` if the feature is disabled.

## Enable 2FA

```http
POST /api/auth/2fa/enable/
Authorization: Bearer <access_token>
Content-Type: application/json
```

Body: `{"code": "123456"}`, exactly six characters, taken from the authenticator app.

`200 OK`:

```json
{
  "message": "Two-factor authentication is enabled.",
  "recovery_codes": ["A1B2C3D4-E5F6A7B8", "..."]
}
```

Recovery codes are returned only here and when they are regenerated; the server keeps only hashes. `400` if setup was never started or has expired, or if the code is wrong. Enabling 2FA changes the user's `auth_version`, so the tokens you hold stop working. Log in again.

## Disable 2FA

```http
POST /api/auth/2fa/disable/
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{ "password": "StrongPass123!", "code": "123456" }
```

Needs the password and a current TOTP code; recovery codes are not accepted here. `200 OK`: `{"message": "Two-factor authentication is disabled. Please log in again."}`. Existing tokens are invalidated and the recovery codes are deleted. `400` for a wrong password or code, or if 2FA is not enabled.

## Replace recovery codes

```http
POST /api/auth/2fa/recovery-codes/
Authorization: Bearer <access_token>
Content-Type: application/json
```

Same body as disable. Replaces all recovery codes, so older ones stop working, and returns `{"recovery_codes": [...]}`. Existing tokens stay valid.

## Related pages

- [API overview]({{ '/api-reference/' | relative_url }})
- [Statement endpoints]({{ '/api-reference/statements/' | relative_url }})
- [Account and privacy endpoints]({{ '/api-reference/account/' | relative_url }})
