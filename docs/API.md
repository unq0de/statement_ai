# Statement AI API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication--tokens)
3. [Rate Limiting](#rate-limiting-details)
4. [Status Codes Reference](#status-codes-reference)
5. [Error Handling](#error-handling)
6. [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa-complete-flow)
7. [Authentication Endpoints](#authentication-endpoints)
8. [Statement Endpoints](#statement-endpoints)
9. [Transaction Endpoints](#transaction-endpoints)
10. [Request/Response Schemas](#requestresponse-schemas)
11. [Data Validation & Requirements](#data-validation--requirements)
12. [Common Workflows & Examples](#common-workflows--examples)
13. [Health Check](#health-check-endpoint)

## Overview

Statement AI is a REST API for managing bank statements and financial transactions. The API provides secure authentication, statement uploading, AI-powered analysis, and transaction querying capabilities.

### Base URL

```
https://api.statementai.com
```

For local development:
```
http://localhost:8000
```

### Authentication Method

All endpoints (except registration) require authentication using **JWT Bearer tokens**. Include your access token in the `Authorization` header:

```
Authorization: Bearer <your_access_token>
```

Access tokens are valid for **60 minutes**. Use the refresh token to obtain a new access token.

### CORS & HTTPS

- **HTTPS Required**: All production API calls must use HTTPS (port 443)
- **CORS Enabled**: The API supports Cross-Origin Resource Sharing for web applications
- **Development**: Local development uses HTTP on port 8000 without strict CORS requirements

### Rate Limiting Overview

The API implements rate limiting to ensure fair usage and system stability. Rate limits vary by endpoint type:

- **Anonymous Users**: 60 requests/minute (before registration)
- **Authenticated Users**: 120 requests/minute (general operations)
- **Sensitive Operations**: Lower limits on password reset, 2FA, and registration (see [Rate Limiting Details](#rate-limiting-details))

Rate limit headers are included in every response:
- `X-RateLimit-Limit`: Maximum requests in the current window
- `X-RateLimit-Remaining`: Requests remaining in the current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

When rate limited (HTTP 429), check the `Retry-After` header for how long to wait before retrying.

---

## Authentication & Tokens

### JWT Bearer Token Authentication

All authenticated endpoints require a Bearer token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  https://api.statementai.com/api/statements/
```

### Token Lifetimes

- **Access Token**: Valid for 60 minutes (3600 seconds)
- **Refresh Token**: Valid for 1 day (86400 seconds)

### Token Refresh Flow

When your access token expires, use the refresh token to obtain a new access token without logging in again:

```bash
curl -X POST https://api.statementai.com/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

The refresh endpoint returns a new access token. Store both tokens securely on the client.

### What Causes Token Revocation

Tokens are revoked in these scenarios:

- User logs out
- User password is changed
- User account is deleted
- User disables 2FA (requires re-authentication)
- Token expires naturally (use refresh token to extend access)

Once revoked, you must log in again to obtain new tokens.

---

## Rate Limiting Details

The API implements the following rate limits by operation:

| Operation | Limit | Window |
|-----------|-------|--------|
| Anonymous requests | 60 | 1 minute |
| Authenticated requests | 120 | 1 minute |
| User registration | 5 | 1 hour |
| Email confirmation | 10 | 1 hour |
| Resend confirmation email | 3 | 1 hour |
| Two-factor management | 10 | 1 hour |
| Two-factor login | 10 | 1 hour |
| Login attempts | 10 | 1 minute |
| Password reset requests | 5 | 1 hour |
| Password reset email sends | 3 | 1 hour |
| Password reset confirmation | 10 | 1 hour |
| Statement upload | 5 | 1 hour |

### Handling 429 (Too Many Requests)

When you exceed the rate limit, the API returns HTTP 429 with:

```json
{
  "detail": "Request rate limit exceeded.",
  "retry_after": 60
}
```

The `Retry-After` header indicates seconds to wait:

```
Retry-After: 60
```

**Best Practice**: Implement exponential backoff with jitter in your client:

```python
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = func()
            if response.status_code == 429:
                wait_time = int(response.headers.get('Retry-After', 60))
                jitter = random.uniform(0, 1)
                time.sleep(wait_time + jitter)
                continue
            return response
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
```

---

## Status Codes Reference

Statement AI uses standard HTTP status codes:

| Code | Name | Description |
|------|------|-------------|
| **200** | OK | Successful request; response includes requested data |
| **201** | Created | Resource successfully created (typically POST requests) |
| **202** | Accepted | Request accepted for processing (async operations like statement uploads) |
| **400** | Bad Request | Invalid request body or query parameters; see error details |
| **401** | Unauthorized | Missing or invalid authentication token |
| **403** | Forbidden | User lacks permission for this resource (e.g., accessing another user's statement) |
| **404** | Not Found | Resource doesn't exist (e.g., statement ID not found) |
| **409** | Conflict | Request conflicts with current state (e.g., email already registered) |
| **429** | Too Many Requests | Rate limit exceeded; see `Retry-After` header |
| **503** | Service Unavailable | Server temporarily unavailable; retry after delay |

---

## Error Handling

### Standard Error Response Format

All errors return JSON with consistent structure:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors, individual field errors are included:

```json
{
  "detail": "Validation failed",
  "errors": {
    "email": ["Must be a valid email address"],
    "password": ["Password must be at least 8 characters"]
  }
}
```

### Common Error Codes & Messages

**Authentication Errors:**

| HTTP Code | Message | Cause |
|-----------|---------|-------|
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 401 | `"Invalid token"` | Token malformed or invalid |
| 401 | `"Token expired"` | Access token lifetime exceeded; use refresh token |
| 401 | `"Token revoked"` | Token was explicitly revoked (e.g., password changed) |

**Validation Errors:**

| Field | Error Message | Requirement |
|-------|---------------|-------------|
| `email` | `"Must be a valid email address"` | RFC 5322 format |
| `email` | `"Email already registered"` | Email must be unique |
| `username` | `"Username must be 3-30 characters"` | 3-30 alphanumeric + underscore |
| `password` | `"Password must be at least 8 characters"` | Minimum 8 characters |
| `password` | `"Password too common"` | Must not be in common password list |
| `password` | `"Password cannot contain username"` | Must not match username |

**Resource Errors:**

| HTTP Code | Message | Scenario |
|-----------|---------|----------|
| 404 | `"Statement not found"` | Invalid statement ID |
| 404 | `"Transaction not found"` | Invalid transaction ID |
| 409 | `"Email already registered"` | Duplicate email during registration |
| 400 | `"File must be PDF format"` | Upload non-PDF file |
| 400 | `"File size exceeds 10 MB"` | Upload file larger than limit |

---

## Two-Factor Authentication (2FA) Complete Flow

### 2FA Overview

Two-factor authentication adds a second layer of security using time-based one-time passwords (TOTP) via authenticator apps like Google Authenticator, Authy, or Microsoft Authenticator.

**Key Parameters:**
- Challenge timeout: 300 seconds (5 minutes)
- Max attempts per challenge: 5
- Recovery codes generated: 10 codes (32 characters each)
- Users must save recovery codes immediately after enabling 2FA

### 2FA Setup Flow

**Step 1: Initiate 2FA Setup**

```bash
curl -X POST https://api.statementai.com/api/auth/2fa/setup/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Response includes QR code and secret:

```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgo...",
  "secret": "JBSWY3DPEBLW64TMMQ======",
  "setup_token": "temp_token_123..."
}
```

**Step 2: Scan QR Code**

User scans the QR code in their authenticator app. The app generates 6-digit codes that refresh every 30 seconds.

**Step 3: Verify and Enable 2FA**

```bash
curl -X POST https://api.statementai.com/api/auth/2fa/enable/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456",
    "setup_token": "temp_token_123..."
  }'
```

Success response includes recovery codes:

```json
{
  "status": "enabled",
  "recovery_codes": [
    "AAAA-AAAA-AAAA-AAAA",
    "BBBB-BBBB-BBBB-BBBB",
    ...
  ],
  "message": "Save these recovery codes in a secure location. Each code can be used once if you lose access to your authenticator app."
}
```

**Important**: Users must save recovery codes immediately. They won't be shown again.

### Login Flow with 2FA Enabled

**Step 1: Login Request**

```bash
curl -X POST https://api.statementai.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

If 2FA is enabled, instead of returning tokens, the API returns a challenge:

```json
{
  "2fa_required": true,
  "challenge_id": "ch_123456789abcdef",
  "expires_at": "2024-11-08T17:00:00Z"
}
```

**Step 2: Provide 2FA Code or Recovery Code**

The user has 300 seconds to provide either:
- A 6-digit code from their authenticator app (changes every 30 seconds)
- One of their 10 recovery codes (32 characters, used once)

```bash
curl -X POST https://api.statementai.com/api/auth/login/2fa/ \
  -H "Content-Type: application/json" \
  -d '{
    "challenge_id": "ch_123456789abcdef",
    "code": "123456"
  }'
```

Or with recovery code:

```bash
curl -X POST https://api.statementai.com/api/auth/login/2fa/ \
  -H "Content-Type: application/json" \
  -d '{
    "challenge_id": "ch_123456789abcdef",
    "recovery_code": "AAAA-AAAA-AAAA-AAAA"
  }'
```

Success response (after correct code):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Step 3: Handle Errors**

If code is incorrect (max 5 attempts per challenge):

```json
{
  "detail": "Invalid 2FA code. Attempts remaining: 4"
}
```

After 5 failed attempts:

```json
{
  "detail": "Maximum login attempts exceeded. Please try again.",
  "challenge_expired": true
}
```

### Disable 2FA Flow

Disabling requires the user's password AND a current 2FA code:

```bash
curl -X POST https://api.statementai.com/api/auth/2fa/disable/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "password123",
    "code": "123456"
  }'
```

Response:

```json
{
  "status": "disabled",
  "message": "Two-factor authentication has been disabled. You will need to enter your password to re-enable it."
}
```

### Regenerate Recovery Codes

Users can regenerate recovery codes (invalidates old ones):

```bash
curl -X POST https://api.statementai.com/api/auth/2fa/recovery-codes/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456"
  }'
```

Response includes new codes (same as Step 3 of setup flow):

```json
{
  "recovery_codes": [
    "AAAA-AAAA-AAAA-AAAA",
    "BBBB-BBBB-BBBB-BBBB",
    ...
  ],
  "message": "Recovery codes regenerated. Old codes are no longer valid."
}
```

---

## Authentication Endpoints

### POST /api/auth/register/

**Create a new user account.**

- **Authentication Required**: No
- **Rate Limit**: 5 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePassword123"
}
```

#### Success Response (201 Created)

```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "message": "Registration successful. Please check your email to confirm your account."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Username must be 3-30 characters"` | Username too short or too long |
| 400 | `"Username contains invalid characters"` | Only alphanumeric + underscore allowed |
| 400 | `"Must be a valid email address"` | Email format invalid |
| 409 | `"Email already registered"` | Email already exists |
| 409 | `"Username already taken"` | Username already exists |
| 400 | `"Password must be at least 8 characters"` | Password too short |
| 400 | `"Password too common"` | Password in common password list |
| 400 | `"Password cannot contain username"` | Password too similar to username |
| 429 | `"Rate limit exceeded"` | Max 5 registrations/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePassword123"
  }'
```

#### Description

Creates a new user account and sends a confirmation email to the provided address. The account is inactive until the user confirms their email. Passwords must meet security requirements and cannot be common passwords or variations of the username.

---

### POST /api/auth/register/confirm/

**Confirm email address with confirmation code.**

- **Authentication Required**: No
- **Rate Limit**: 10 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "email": "john@example.com",
  "code": "123456"
}
```

#### Success Response (200 OK)

```json
{
  "detail": "Email confirmed successfully. You can now log in."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Invalid confirmation code"` | Code is incorrect or expired |
| 400 | `"Email not found"` | Email not registered |
| 400 | `"Email already confirmed"` | Email already verified |
| 429 | `"Rate limit exceeded"` | Max 10 confirmations/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/register/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "code": "123456"
  }'
```

#### Description

Confirms the user's email using the code sent to their email address during registration. Codes expire after 24 hours. The user cannot log in until their email is confirmed.

---

### POST /api/auth/register/resend-confirmation/

**Resend confirmation email.**

- **Authentication Required**: No
- **Rate Limit**: 3 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "email": "john@example.com"
}
```

#### Success Response (200 OK)

```json
{
  "detail": "Confirmation email sent. Please check your inbox."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Email not found"` | Email not registered |
| 400 | `"Email already confirmed"` | Email already verified |
| 429 | `"Rate limit exceeded"` | Max 3 resends/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/register/resend-confirmation/ \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'
```

#### Description

Resends the confirmation email if the user didn't receive it or their code expired. Useful for recovering from deletion of the original email.

---

### POST /api/auth/login/

**Authenticate user and receive tokens (or 2FA challenge if enabled).**

- **Authentication Required**: No
- **Rate Limit**: 10 requests/minute
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "email": "john@example.com",
  "password": "SecurePassword123"
}
```

#### Success Response (200 OK) - Without 2FA

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

#### Success Response (200 OK) - With 2FA Enabled

```json
{
  "2fa_required": true,
  "challenge_id": "ch_123456789abcdef",
  "expires_at": "2024-11-08T17:00:00Z",
  "message": "2FA required. Send your code to /api/auth/login/2fa/"
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 401 | `"Invalid email or password"` | Credentials incorrect |
| 400 | `"Email not confirmed"` | User hasn't confirmed email |
| 429 | `"Rate limit exceeded"` | Max 10 login attempts/minute |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123"
  }'
```

#### Description

Authenticates a user with email and password. Returns access and refresh tokens for authenticated requests. If 2FA is enabled, returns a challenge ID instead of tokens. Credentials must be exactly correct; the API doesn't distinguish between invalid email and invalid password for security.

---

### POST /api/auth/login/2fa/

**Complete 2FA login with authenticator code or recovery code.**

- **Authentication Required**: No
- **Rate Limit**: 10 requests/hour
- **Content-Type**: `application/json`

#### Request Body (With Authenticator Code)

```json
{
  "challenge_id": "ch_123456789abcdef",
  "code": "123456"
}
```

#### Request Body (With Recovery Code)

```json
{
  "challenge_id": "ch_123456789abcdef",
  "recovery_code": "AAAA-AAAA-AAAA-AAAA"
}
```

#### Success Response (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Invalid challenge ID"` | Challenge doesn't exist |
| 400 | `"Challenge expired"` | 5 minutes have passed |
| 400 | `"Invalid 2FA code. Attempts remaining: 4"` | Code incorrect (max 5 attempts) |
| 400 | `"Invalid recovery code"` | Code incorrect or already used |
| 400 | `"Maximum login attempts exceeded"` | 5 failed attempts; must retry from login |
| 429 | `"Rate limit exceeded"` | Max 10 2FA attempts/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/login/2fa/ \
  -H "Content-Type: application/json" \
  -d '{
    "challenge_id": "ch_123456789abcdef",
    "code": "123456"
  }'
```

#### Description

Completes 2FA login by verifying the code from the user's authenticator app or using a recovery code. The challenge expires after 300 seconds and allows maximum 5 failed attempts before requiring a new login.

---

### POST /api/auth/refresh/

**Refresh access token using refresh token.**

- **Authentication Required**: No
- **Rate Limit**: 120 requests/minute (authenticated limit)
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Success Response (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 401 | `"Invalid refresh token"` | Token malformed or invalid |
| 401 | `"Refresh token expired"` | Token valid for 1 day only |
| 401 | `"Token revoked"` | User changed password or logged out |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

#### Description

Obtains a new access token using a valid refresh token. Useful when your access token expires (after 60 minutes). Refresh tokens are valid for 1 day. Once expired, user must log in again.

---

### POST /api/auth/password-reset/

**Request password reset (sends email with code).**

- **Authentication Required**: No
- **Rate Limit**: 5 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "email": "john@example.com"
}
```

#### Success Response (200 OK)

```json
{
  "detail": "If this email is registered, you'll receive a password reset link shortly."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 429 | `"Rate limit exceeded"` | Max 5 reset requests/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/password-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'
```

#### Description

Initiates password reset by sending an email with a reset code. The endpoint returns success regardless of whether the email exists (for security). Reset codes expire after 24 hours. The response doesn't indicate whether the email was found.

---

### POST /api/auth/password-reset/confirm/

**Confirm password reset with code and new password.**

- **Authentication Required**: No
- **Rate Limit**: 10 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "email": "john@example.com",
  "code": "123456",
  "new_password": "NewSecurePassword456"
}
```

#### Success Response (200 OK)

```json
{
  "detail": "Password reset successfully. You can now log in with your new password."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Invalid reset code"` | Code incorrect or expired |
| 400 | `"Email not found"` | Email not registered |
| 400 | `"Password must be at least 8 characters"` | Password too short |
| 400 | `"Password too common"` | Password in common password list |
| 400 | `"Password cannot contain username"` | Password too similar to username |
| 429 | `"Rate limit exceeded"` | Max 10 resets/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/password-reset/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "code": "123456",
    "new_password": "NewSecurePassword456"
  }'
```

#### Description

Completes password reset using the code sent via email. New password must meet security requirements. All previous tokens are invalidated after password reset; user must log in again.

---

### GET /api/auth/2fa/

**Get current 2FA status.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/json`

#### Success Response (200 OK)

```json
{
  "enabled": false,
  "last_setup_at": null,
  "recovery_codes_count": 0
}
```

Or if enabled:

```json
{
  "enabled": true,
  "last_setup_at": "2024-11-01T14:30:00Z",
  "recovery_codes_count": 10
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 401 | `"Invalid token"` | Token malformed or invalid |

#### Curl Example

```bash
curl -X GET https://api.statementai.com/api/auth/2fa/ \
  -H "Authorization: Bearer <token>"
```

#### Description

Retrieves the current 2FA status for the authenticated user, including whether it's enabled and how many recovery codes remain unused.

---

### POST /api/auth/2fa/setup/

**Initiate 2FA setup (returns QR code and secret).**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 10 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{}
```

#### Success Response (200 OK)

```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAA...",
  "secret": "JBSWY3DPEBLW64TMMQ======",
  "setup_token": "setup_token_abc123def456ghi789",
  "message": "Scan the QR code with your authenticator app, or enter the secret manually. Then call /2fa/enable/ with the code."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 400 | `"2FA already enabled"` | User already has 2FA active |
| 429 | `"Rate limit exceeded"` | Max 10 setup attempts/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/2fa/setup/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Description

Starts 2FA setup by generating a TOTP secret and QR code. The user scans the QR code in their authenticator app (Google Authenticator, Authy, etc). The setup_token is valid for 10 minutes. After scanning, call /2fa/enable/ with the 6-digit code from the app.

---

### POST /api/auth/2fa/enable/

**Enable 2FA with verification code.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 10 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "code": "123456",
  "setup_token": "setup_token_abc123def456ghi789"
}
```

#### Success Response (200 OK)

```json
{
  "status": "enabled",
  "recovery_codes": [
    "AAAA-AAAA-AAAA-AAAA",
    "BBBB-BBBB-BBBB-BBBB",
    "CCCC-CCCC-CCCC-CCCC",
    "DDDD-DDDD-DDDD-DDDD",
    "EEEE-EEEE-EEEE-EEEE",
    "FFFF-FFFF-FFFF-FFFF",
    "GGGG-GGGG-GGGG-GGGG",
    "HHHH-HHHH-HHHH-HHHH",
    "IIII-IIII-IIII-IIII",
    "JJJJ-JJJJ-JJJJ-JJJJ"
  ],
  "message": "Two-factor authentication has been enabled. Save your recovery codes in a secure location. Each code can be used once if you lose access to your authenticator app."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Invalid verification code"` | Code incorrect (6 digits required) |
| 400 | `"Invalid setup token"` | Setup token expired or invalid |
| 400 | `"2FA already enabled"` | User already has 2FA active |
| 429 | `"Rate limit exceeded"` | Max 10 enable attempts/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/2fa/enable/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456",
    "setup_token": "setup_token_abc123def456ghi789"
  }'
```

#### Description

Enables 2FA after the user has scanned the QR code and provides the verification code from their authenticator app. Returns 10 recovery codes that should be saved immediately. Recovery codes are the only way to access the account if the authenticator app is lost.

---

### POST /api/auth/2fa/disable/

**Disable 2FA (requires password and current code).**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 10 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "password": "SecurePassword123",
  "code": "123456"
}
```

#### Success Response (200 OK)

```json
{
  "status": "disabled",
  "message": "Two-factor authentication has been disabled. Recovery codes are no longer valid."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"2FA not enabled"` | User doesn't have 2FA active |
| 400 | `"Invalid password"` | Password incorrect |
| 400 | `"Invalid 2FA code"` | Code incorrect or expired |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 429 | `"Rate limit exceeded"` | Max 10 disable attempts/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/2fa/disable/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "SecurePassword123",
    "code": "123456"
  }'
```

#### Description

Disables 2FA after verifying the user's password and providing a current code from their authenticator app. This prevents accidental disabling. All recovery codes are invalidated. User must enter their password and 2FA code again to re-enable 2FA.

---

### POST /api/auth/2fa/recovery-codes/

**Regenerate recovery codes (invalidates old codes).**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 10 requests/hour
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "code": "123456"
}
```

#### Success Response (200 OK)

```json
{
  "recovery_codes": [
    "AAAA-AAAA-AAAA-AAAA",
    "BBBB-BBBB-BBBB-BBBB",
    "CCCC-CCCC-CCCC-CCCC",
    "DDDD-DDDD-DDDD-DDDD",
    "EEEE-EEEE-EEEE-EEEE",
    "FFFF-FFFF-FFFF-FFFF",
    "GGGG-GGGG-GGGG-GGGG",
    "HHHH-HHHH-HHHH-HHHH",
    "IIII-IIII-IIII-IIII",
    "JJJJ-JJJJ-JJJJ-JJJJ"
  ],
  "message": "Recovery codes regenerated. Previous recovery codes are no longer valid."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"2FA not enabled"` | User doesn't have 2FA active |
| 400 | `"Invalid 2FA code"` | Code incorrect or expired |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 429 | `"Rate limit exceeded"` | Max 10 regenerate attempts/hour |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/auth/2fa/recovery-codes/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'
```

#### Description

Regenerates a new set of 10 recovery codes and invalidates all previous codes. Useful if the user suspects their recovery codes have been compromised or lost track of how many they've used. Requires current 2FA code for verification.

---

### DELETE /api/auth/account/

**Permanently delete user account (requires password).**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 1 request/day
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "password": "SecurePassword123"
}
```

#### Success Response (204 No Content)

No response body returned.

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Invalid password"` | Password incorrect |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 429 | `"Rate limit exceeded"` | Limited to 1 deletion/day |

#### Curl Example

```bash
curl -X DELETE https://api.statementai.com/api/auth/account/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "SecurePassword123"}'
```

#### Description

Permanently deletes the user's account and all associated data (statements, transactions, settings). This action is irreversible. Requires password confirmation to prevent accidental deletion. A confirmation email is sent before deletion is finalized (user has 24 hours to cancel).

---

### GET /api/auth/export/

**Export all personal data (GDPR compliance).**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 1 request/day
- **Content-Type**: `application/json`

#### Success Response (200 OK)

Returns a ZIP file containing JSON exports of all user data:

```json
{
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "created_at": "2024-01-15T10:00:00Z",
    "last_login": "2024-11-08T14:30:00Z"
  },
  "statements": [
    {
      "id": 1,
      "uploaded_at": "2024-11-01T12:00:00Z",
      "file_name": "statement_nov2024.pdf",
      "processing_status": "completed",
      "ai_evaluation": "..."
    }
  ],
  "transactions": [
    {
      "id": 1,
      "date": "2024-11-01",
      "payee_payer": "Example Bank",
      "description": "Salary",
      "amount": "5000.00",
      "transaction_type": "INCOME"
    }
  ]
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 429 | `"Rate limit exceeded"` | Limited to 1 export/day |

#### Curl Example

```bash
curl -X GET https://api.statementai.com/api/auth/export/ \
  -H "Authorization: Bearer <token>" \
  --output personal_data.zip
```

#### Description

Exports all of the user's personal data in standard JSON format within a ZIP file. Used for GDPR compliance (right to data portability). The export includes user profile, all statements, transactions, and settings. Limited to 1 export per day to prevent abuse.

---

## Statement Endpoints

### GET /api/statements/

**List all statements for the authenticated user (paginated).**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/json`

#### Query Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `page` | integer | No | Page number (1-indexed) | 1 |
| `limit` | integer | No | Results per page (1-100) | 20 |
| `status` | string | No | Filter by status: `pending`, `processing`, `completed`, `failed` | None |
| `sort_by` | string | No | Sort field: `uploaded_at`, `-uploaded_at` (descending) | `-uploaded_at` |
| `date_from` | string | No | Filter statements uploaded on/after (YYYY-MM-DD) | None |
| `date_to` | string | No | Filter statements uploaded on/before (YYYY-MM-DD) | None |

#### Success Response (200 OK)

```json
{
  "results": [
    {
      "id": 1,
      "file_name": "statement_nov2024.pdf",
      "uploaded_at": "2024-11-01T12:00:00Z",
      "processing_status": "completed",
      "is_processed": true,
      "transaction_count": 25
    },
    {
      "id": 2,
      "file_name": "statement_oct2024.pdf",
      "uploaded_at": "2024-10-15T08:30:00Z",
      "processing_status": "processing",
      "is_processed": false,
      "transaction_count": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_count": 2,
    "total_pages": 1
  }
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Invalid page number"` | Page < 1 or not an integer |
| 400 | `"Invalid limit"` | Limit < 1 or > 100 |
| 400 | `"Invalid status filter"` | Status not one of allowed values |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |

#### Curl Example

```bash
curl -X GET 'https://api.statementai.com/api/statements/?page=1&limit=20&status=completed' \
  -H "Authorization: Bearer <token>"
```

#### Description

Retrieves a paginated list of all statements uploaded by the authenticated user. Supports filtering by processing status, date range, and sorting. Useful for building a statements list UI or bulk operations.

---

### POST /api/statements/upload/

**Upload a PDF statement file for processing.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 5 requests/hour
- **Content-Type**: `multipart/form-data`

#### Request

Upload a PDF file using multipart form data:

```bash
curl -X POST https://api.statementai.com/api/statements/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@statement.pdf"
```

#### Success Response (202 Accepted)

```json
{
  "id": 42,
  "file_name": "statement.pdf",
  "uploaded_at": "2024-11-08T16:45:00Z",
  "processing_status": "pending",
  "message": "Statement uploaded successfully. Processing will begin shortly.",
  "status_url": "/api/statements/42/status/"
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"No file provided"` | Missing file in request |
| 400 | `"File must be PDF format"` | File is not a PDF (wrong extension or MIME type) |
| 400 | `"File size exceeds 10 MB"` | File larger than maximum allowed |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 429 | `"Rate limit exceeded"` | Max 5 uploads/hour |
| 503 | `"Service unavailable"` | Processing queue full; try again later |

#### Curl Example

```bash
curl -X POST https://api.statementai.com/api/statements/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@november_statement.pdf"
```

#### Description

Uploads a PDF bank statement for AI processing. The file is queued for extraction and analysis. Returns HTTP 202 (Accepted) because processing is asynchronous. Check the status URL to monitor progress. Files must be in PDF format and under 10 MB. Processing typically completes within 1-2 minutes.

---

### GET /api/statements/{id}/

**Get detailed information about a specific statement.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/json`

#### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Statement ID (from list endpoint) |

#### Success Response (200 OK)

```json
{
  "id": 1,
  "file_name": "statement_nov2024.pdf",
  "uploaded_at": "2024-11-01T12:00:00Z",
  "processing_status": "completed",
  "is_processed": true,
  "ai_evaluation": "Statement analysis shows regular income of $5,000/month with typical monthly expenses of $2,300. Account balance is healthy with consistent positive cash flow.",
  "transactions": [
    {
      "id": 101,
      "date": "2024-11-01",
      "payee_payer": "Employer Inc",
      "description": "Monthly salary",
      "amount": "5000.00",
      "transaction_type": "INCOME"
    },
    {
      "id": 102,
      "date": "2024-11-05",
      "payee_payer": "Electric Company",
      "description": "Monthly bill",
      "amount": "-120.50",
      "transaction_type": "DIRECT_DEBIT"
    }
  ]
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 404 | `"Statement not found"` | Statement ID doesn't exist or belongs to another user |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 403 | `"Permission denied"` | Attempting to access another user's statement |

#### Curl Example

```bash
curl -X GET https://api.statementai.com/api/statements/1/ \
  -H "Authorization: Bearer <token>"
```

#### Description

Retrieves complete details about a specific statement including all extracted transactions and AI evaluation. Only accessible by the statement owner. Returns HTTP 404 if the statement doesn't exist or belongs to another user (no indication of which).

---

### DELETE /api/statements/{id}/

**Delete a single statement.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/json`

#### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Statement ID |

#### Success Response (204 No Content)

No response body returned.

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 404 | `"Statement not found"` | Statement ID doesn't exist |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 403 | `"Permission denied"` | Attempting to delete another user's statement |

#### Curl Example

```bash
curl -X DELETE https://api.statementai.com/api/statements/1/ \
  -H "Authorization: Bearer <token>"
```

#### Description

Permanently deletes a statement and all its associated transactions. This action is irreversible. Returns HTTP 204 (No Content) on success with no response body.

---

### GET /api/statements/{id}/status/

**Check the processing status of a statement.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/json`

#### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Statement ID |

#### Success Response (200 OK)

Processing status response:

```json
{
  "id": 1,
  "processing_status": "completed",
  "is_processed": true,
  "progress": 100,
  "transaction_count": 25,
  "estimated_time_remaining": null,
  "message": "Processing completed successfully."
}
```

Or during processing:

```json
{
  "id": 2,
  "processing_status": "processing",
  "is_processed": false,
  "progress": 45,
  "transaction_count": null,
  "estimated_time_remaining": 30,
  "message": "Extracting transactions from PDF..."
}
```

Or if failed:

```json
{
  "id": 3,
  "processing_status": "failed",
  "is_processed": false,
  "progress": 0,
  "transaction_count": null,
  "estimated_time_remaining": null,
  "error": "Unable to parse PDF. File may be corrupted or in an unsupported format.",
  "message": "Processing failed. Please try uploading the file again."
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 404 | `"Statement not found"` | Statement ID doesn't exist |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |

#### Curl Example

```bash
curl -X GET https://api.statementai.com/api/statements/2/status/ \
  -H "Authorization: Bearer <token>"
```

#### Description

Polls the status of a statement being processed. Returns real-time progress, estimated time remaining, and any error messages. Useful for client-side progress bars. Can be called frequently (respects rate limit).

---

### GET /api/statements/{id}/file/

**Download the original uploaded PDF file.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/pdf`

#### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Statement ID |

#### Success Response (200 OK)

Returns the original PDF file as binary data.

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 404 | `"Statement not found"` | Statement ID doesn't exist |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 403 | `"Permission denied"` | Attempting to download another user's file |

#### Curl Example

```bash
curl -X GET https://api.statementai.com/api/statements/1/file/ \
  -H "Authorization: Bearer <token>" \
  --output my_statement.pdf
```

#### Description

Downloads the original PDF file that was uploaded. Useful for users who want to reference the original document or verify the extracted data. Returns the file as `application/pdf` content type.

---

### GET /api/statements/analytics/

**Retrieve AI evaluations and analytics for all statements.**

**Alternative Endpoint**: `GET /api/analytics/` (alias)

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/json`

#### Query Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `limit` | integer | No | Results per page (1-100) | 20 |
| `page` | integer | No | Page number (1-indexed) | 1 |

#### Success Response (200 OK)

```json
{
  "results": [
    {
      "id": 1,
      "file_name": "statement_nov2024.pdf",
      "uploaded_at": "2024-11-01T12:00:00Z",
      "ai_evaluation": "Statement analysis shows regular income of $5,000/month with typical monthly expenses of $2,300. Account shows healthy cash flow. Recommendations: Consider setting up automatic savings transfer.",
      "summary": {
        "total_income": "15000.00",
        "total_expenses": "6900.00",
        "net_flow": "8100.00",
        "average_transaction_amount": "275.50"
      }
    },
    {
      "id": 2,
      "file_name": "statement_oct2024.pdf",
      "uploaded_at": "2024-10-15T08:30:00Z",
      "ai_evaluation": "...",
      "summary": { ... }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_count": 2
  }
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |

#### Curl Example

```bash
curl -X GET 'https://api.statementai.com/api/statements/analytics/?page=1&limit=10' \
  -H "Authorization: Bearer <token>"
```

#### Description

Retrieves AI-powered analysis and evaluations of all processed statements. Includes natural language insights about cash flow, spending patterns, and financial health. Also accessible via `/api/analytics/` alias. Only returns statements with completed processing.

---

### DELETE /api/statements/delete-all/

**Bulk delete all statements (dangerous operation).**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 1 request/day
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "confirm": true
}
```

#### Success Response (204 No Content)

No response body returned. All statements and associated transactions are deleted.

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Confirmation required"` | Missing or false `confirm` parameter |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |
| 429 | `"Rate limit exceeded"` | Limited to 1 bulk deletion/day |

#### Curl Example

```bash
curl -X DELETE https://api.statementai.com/api/statements/delete-all/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

#### Description

Permanently deletes all statements and transactions for the authenticated user. This is a dangerous operation - requires explicit confirmation. Limited to once per day to prevent accidental data loss. A confirmation email is sent with a 24-hour window to undo the deletion.

---

## Transaction Endpoints

### GET /api/transactions/

**List transactions with optional filtering.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/json`

#### Query Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `page` | integer | No | Page number (1-indexed) | 1 |
| `limit` | integer | No | Results per page (1-100) | 20 |
| `type` | string | No | Filter by type (see transaction types) | None |
| `statement_id` | integer | No | Filter by statement ID | None |
| `date_from` | string | No | Filter transactions on/after (YYYY-MM-DD) | None |
| `date_to` | string | No | Filter transactions on/before (YYYY-MM-DD) | None |
| `amount_min` | decimal | No | Minimum transaction amount | None |
| `amount_max` | decimal | No | Maximum transaction amount | None |
| `search` | string | No | Search in payee/description (substring match) | None |
| `sort_by` | string | No | Sort field: `date`, `-date`, `amount`, `-amount` | `-date` |

#### Success Response (200 OK)

```json
{
  "results": [
    {
      "id": 101,
      "statement_id": 1,
      "date": "2024-11-01",
      "payee_payer": "Employer Inc",
      "description": "Monthly salary",
      "amount": "5000.00",
      "transaction_type": "INCOME",
      "category": "Salary"
    },
    {
      "id": 102,
      "statement_id": 1,
      "date": "2024-11-05",
      "payee_payer": "Electric Company",
      "description": "Monthly bill payment",
      "amount": "-120.50",
      "transaction_type": "DIRECT_DEBIT",
      "category": "Utilities"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_count": 47,
    "total_pages": 3
  }
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 400 | `"Invalid page number"` | Page < 1 or not an integer |
| 400 | `"Invalid transaction type"` | Type not one of allowed values |
| 400 | `"Invalid date format"` | Date not in YYYY-MM-DD format |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |

#### Curl Example

```bash
curl -X GET 'https://api.statementai.com/api/transactions/?type=INCOME&date_from=2024-11-01&sort_by=-date' \
  -H "Authorization: Bearer <token>"
```

#### Description

Retrieves transactions across all statements with flexible filtering. Supports filtering by type, date range, amount, and statement. Useful for financial analysis, categorization, and reporting. Transactions are listed chronologically by default (newest first).

---

### GET /api/transactions/{id}/

**Get details about a specific transaction.**

- **Authentication Required**: Yes (Bearer token)
- **Rate Limit**: 120 requests/minute
- **Content-Type**: `application/json`

#### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Transaction ID |

#### Success Response (200 OK)

```json
{
  "id": 101,
  "statement_id": 1,
  "date": "2024-11-01",
  "payee_payer": "Employer Inc",
  "description": "Monthly salary - November 2024",
  "amount": "5000.00",
  "transaction_type": "INCOME",
  "category": "Salary",
  "notes": null,
  "created_at": "2024-11-01T12:15:00Z"
}
```

#### Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 404 | `"Transaction not found"` | Transaction ID doesn't exist or belongs to another user |
| 401 | `"Authentication credentials not provided"` | Missing Authorization header |

#### Curl Example

```bash
curl -X GET https://api.statementai.com/api/transactions/101/ \
  -H "Authorization: Bearer <token>"
```

#### Description

Retrieves full details about a specific transaction. Only accessible by the user who owns the statement containing the transaction. Returns HTTP 404 if the transaction doesn't exist or belongs to another user.

---

## Request/Response Schemas

### User Object

```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "created_at": "2024-01-15T10:00:00Z",
  "last_login": "2024-11-08T14:30:00Z",
  "is_email_verified": true,
  "two_factor_enabled": false
}
```

### BankStatement Object

```json
{
  "id": 1,
  "file_name": "statement_nov2024.pdf",
  "file_size_bytes": 524288,
  "uploaded_at": "2024-11-01T12:00:00Z",
  "processing_status": "completed",
  "is_processed": true,
  "ai_evaluation": "Detailed AI analysis text...",
  "transaction_count": 25,
  "processing_completed_at": "2024-11-01T12:02:15Z",
  "error_message": null,
  "transactions": [
    { "id": 101, "date": "2024-11-01", ... },
    { "id": 102, "date": "2024-11-05", ... }
  ]
}
```

**Processing Status Enum:**
- `pending` - Statement received, waiting to be processed
- `processing` - Currently extracting data and analyzing
- `completed` - Successfully processed; transactions available
- `failed` - Processing error; check error_message

### Transaction Object

```json
{
  "id": 101,
  "statement_id": 1,
  "date": "2024-11-01",
  "payee_payer": "Employer Inc",
  "description": "Monthly salary - November 2024",
  "amount": "5000.00",
  "transaction_type": "INCOME",
  "category": "Salary",
  "notes": null,
  "created_at": "2024-11-01T12:15:00Z"
}
```

**Transaction Type Enum:**
- `INCOME` - Money received (salary, bonus, refund)
- `TRANSFER_OUT` - Money sent to another account
- `TRANSFER_IN` - Money received from another account
- `DIRECT_DEBIT` - Automatic payment (bills, subscriptions)
- `STANDING_ORDER` - Recurring scheduled payment
- `CARD_PAYMENT` - Debit/credit card transaction
- `ATM_WITHDRAWAL` - Cash withdrawal from ATM
- `FEE_CHARGE` - Bank fees or charges

### Error Response Format

**Standard error (single message):**

```json
{
  "detail": "Human-readable error description"
}
```

**Validation error (multiple field errors):**

```json
{
  "detail": "Validation failed",
  "errors": {
    "field_name": ["Error message 1", "Error message 2"],
    "another_field": ["Error message"]
  }
}
```

**Rate limit error:**

```json
{
  "detail": "Request rate limit exceeded.",
  "retry_after": 60
}
```

---

## Data Validation & Requirements

### Username Requirements

- **Length**: 3-30 characters
- **Characters**: Alphanumeric (a-z, A-Z, 0-9) and underscores (_) only
- **Uniqueness**: Must be unique across all users
- **Valid Examples**: `john_doe`, `user123`, `test_user_99`
- **Invalid Examples**: `ab` (too short), `john@doe` (invalid char), `john-doe` (invalid char)

### Email Requirements

- **Format**: RFC 5322 standard email format
- **Uniqueness**: Must be unique across all users
- **Verification**: Must be confirmed via confirmation email before account access
- **Valid Examples**: `user@example.com`, `john.doe+tag@company.co.uk`
- **Invalid Examples**: `invalid.email@`, `user@domain`, `user name@example.com`

### Password Requirements

- **Minimum Length**: 8 characters
- **Complexity**: No explicit complexity requirement, but must not be in common password list
- **Restrictions**:
  - Cannot match or closely resemble username
  - Cannot be a commonly used password (checked against standard list)
  - Case-sensitive (passwords are case-sensitive)
- **Valid Examples**: `SecurePass123`, `MyDog$Eats#Pizza`, `correct-horse-battery-staple`
- **Invalid Examples**: `12345678` (too common), `johnjohnjohn` (matches username), `pass` (too short)

### File Upload Constraints

- **Format**: PDF only (`.pdf` extension and `application/pdf` MIME type)
- **Maximum Size**: 10 MB (10,485,760 bytes)
- **Processing**: Asynchronous; typically completes in 1-2 minutes
- **Supported**: Bank statements from most major institutions

### Transaction Type Options

```
INCOME              - Money received (salary, bonus, refund)
TRANSFER_OUT        - Money sent to another account  
TRANSFER_IN         - Money received from another account
DIRECT_DEBIT        - Automatic payment (bills, subscriptions)
STANDING_ORDER      - Recurring scheduled payment
CARD_PAYMENT        - Debit/credit card transaction
ATM_WITHDRAWAL      - Cash withdrawal from ATM
FEE_CHARGE          - Bank fees or charges
```

### Field Type Constraints

| Field | Type | Max Length | Notes |
|-------|------|-----------|-------|
| `id` | Integer | - | Auto-generated primary key |
| `username` | String | 30 | Alphanumeric + underscore |
| `email` | String | 254 | RFC 5322 format |
| `password` | String | 128 | Hashed before storage |
| `payee_payer` | String | 255 | Name of party in transaction |
| `description` | Text | 1000 | Transaction description |
| `amount` | Decimal | - | Fixed to 2 decimal places |
| `category` | String | 60 | Transaction category |
| `date` | Date | - | Format: YYYY-MM-DD |
| `uploaded_at` | DateTime | - | ISO 8601 format with timezone |
| `ai_evaluation` | Text | 10000 | AI-generated analysis |

---

## Common Workflows & Examples

### Complete Registration Workflow

```bash
# Step 1: Register user
curl -X POST https://api.statementai.com/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePassword123"
  }'
# Response: User ID and confirmation sent to email

# Step 2: User receives confirmation code via email
# (In real workflow, user checks their email inbox)

# Step 3: Confirm email
curl -X POST https://api.statementai.com/api/auth/register/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "code": "123456"
  }'
# Response: Email confirmed, account is now active

# Step 4: Login to get tokens
curl -X POST https://api.statementai.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123"
  }'
# Response: access_token, refresh_token (ready to make authenticated requests)
```

### Password Reset Workflow

```bash
# Step 1: Request password reset
curl -X POST https://api.statementai.com/api/auth/password-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'
# Response: "Check your email for reset instructions"

# Step 2: User receives reset code via email
# (In real workflow, user checks email and gets code)

# Step 3: Confirm password reset with new password
curl -X POST https://api.statementai.com/api/auth/password-reset/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "code": "654321",
    "new_password": "NewSecurePassword456"
  }'
# Response: Password reset successfully

# Step 4: Login with new password
curl -X POST https://api.statementai.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "NewSecurePassword456"
  }'
# Response: access_token, refresh_token
```

### 2FA Setup Workflow

```bash
# Step 1: Initiate 2FA setup
curl -X POST https://api.statementai.com/api/auth/2fa/setup/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'
# Response: QR code, secret, setup_token

# Step 2: User scans QR code in authenticator app
# (Google Authenticator, Authy, Microsoft Authenticator, etc)
# App generates 6-digit codes that refresh every 30 seconds

# Step 3: Enable 2FA by confirming code from app
curl -X POST https://api.statementai.com/api/auth/2fa/enable/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456",
    "setup_token": "setup_token_abc123def456ghi789"
  }'
# Response: recovery_codes array (10 backup codes)

# Step 4: User saves recovery codes securely
# (This is critical - they're the only backup if app is lost)
```

### Login with 2FA Enabled

```bash
# Step 1: Initial login attempt
curl -X POST https://api.statementai.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123"
  }'
# Response: 2fa_required: true, challenge_id, expires_at

# Step 2: User provides 2FA code from authenticator app
curl -X POST https://api.statementai.com/api/auth/login/2fa/ \
  -H "Content-Type: application/json" \
  -d '{
    "challenge_id": "ch_123456789abcdef",
    "code": "123456"
  }'
# Response: access_token, refresh_token (success)

# OR if user lost authenticator app, use recovery code
curl -X POST https://api.statementai.com/api/auth/login/2fa/ \
  -H "Content-Type: application/json" \
  -d '{
    "challenge_id": "ch_123456789abcdef",
    "recovery_code": "AAAA-AAAA-AAAA-AAAA"
  }'
# Response: access_token, refresh_token (success, recovery code consumed)
```

### Login Without 2FA

```bash
# Straightforward login without 2FA
curl -X POST https://api.statementai.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123"
  }'
# Response: access_token, refresh_token, expires_in: 3600
```

### Upload and Process a Statement

```bash
# Step 1: Upload PDF statement
curl -X POST https://api.statementai.com/api/statements/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@november_statement.pdf"
# Response: id: 42, processing_status: "pending", status_url

# Step 2: Poll status until processing completes
for i in {1..30}; do
  curl -X GET https://api.statementai.com/api/statements/42/status/ \
    -H "Authorization: Bearer <token>"
  # Check processing_status in response
  # If "completed", processing finished
  sleep 2
done

# Step 3: Get full statement details with transactions
curl -X GET https://api.statementai.com/api/statements/42/ \
  -H "Authorization: Bearer <token>"
# Response: Full statement object with transactions array and AI evaluation

# Step 4: Download original PDF if needed
curl -X GET https://api.statementai.com/api/statements/42/file/ \
  -H "Authorization: Bearer <token>" \
  --output downloaded_statement.pdf
```

### Query Transactions with Filtering

```bash
# Get all income transactions from November 2024
curl -X GET 'https://api.statementai.com/api/transactions/?type=INCOME&date_from=2024-11-01&date_to=2024-11-30' \
  -H "Authorization: Bearer <token>"

# Get all expenses (negative amounts) in specific amount range
curl -X GET 'https://api.statementai.com/api/transactions/?amount_min=-1000&amount_max=0&sort_by=-amount' \
  -H "Authorization: Bearer <token>"

# Search for transactions from specific payee
curl -X GET 'https://api.statementai.com/api/transactions/?search=Electric+Company' \
  -H "Authorization: Bearer <token>"

# Get paginated results (20 per page)
curl -X GET 'https://api.statementai.com/api/transactions/?page=2&limit=20&sort_by=-date' \
  -H "Authorization: Bearer <token>"
```

### Delete Account

```bash
# Step 1: Request account deletion
curl -X DELETE https://api.statementai.com/api/auth/account/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "SecurePassword123"}'
# Response: 204 No Content

# Step 2: User receives confirmation email with 24-hour cancellation window
# (At this point, account still exists but is marked for deletion)

# Step 3: After 24 hours, account is permanently deleted
# All statements, transactions, and personal data are removed
```

---

## Health Check Endpoint

### GET /health/

**Check API health status and dependencies.**

- **Authentication Required**: No
- **Rate Limit**: No limit (health checks exempt)
- **Content-Type**: `application/json`

#### Success Response (200 OK)

```json
{
  "status": "healthy",
  "timestamp": "2024-11-08T16:52:46Z",
  "database": {
    "status": "connected",
    "response_time_ms": 2
  },
  "cache": {
    "status": "connected",
    "response_time_ms": 1
  },
  "api_version": "1.0.0"
}
```

#### Degraded Response (503 Service Unavailable)

```json
{
  "status": "degraded",
  "timestamp": "2024-11-08T16:52:46Z",
  "database": {
    "status": "connected",
    "response_time_ms": 2
  },
  "cache": {
    "status": "disconnected",
    "error": "Connection refused"
  },
  "api_version": "1.0.0"
}
```

#### Curl Example

```bash
curl -X GET https://api.statementai.com/health/
```

#### Description

Provides a health check of the API and its dependencies. Returns status of the database connection and cache system. Useful for monitoring and load balancer health checks. Always returns quickly and doesn't require authentication.

---

## Advanced Topics

### Token Refresh Strategy

For long-running applications, implement automatic token refresh to avoid re-authentication:

```python
import time
import requests

class APIClient:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    def login(self):
        response = requests.post(
            'https://api.statementai.com/api/auth/login/',
            json={'email': self.email, 'password': self.password}
        )
        data = response.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.token_expires_at = time.time() + data['expires_in']
    
    def refresh_if_needed(self):
        if time.time() > self.token_expires_at - 300:  # Refresh 5 min before expiry
            response = requests.post(
                'https://api.statementai.com/api/auth/refresh/',
                json={'refresh_token': self.refresh_token}
            )
            data = response.json()
            self.access_token = data['access_token']
            self.token_expires_at = time.time() + data['expires_in']
    
    def get_headers(self):
        self.refresh_if_needed()
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def get_statements(self):
        response = requests.get(
            'https://api.statementai.com/api/statements/',
            headers=self.get_headers()
        )
        return response.json()
```

### Handling 2FA with Recovery Codes

If a user loses their authenticator app, recovery codes are the backup:

```python
def login_with_recovery_code(email, password, challenge_id, recovery_code):
    response = requests.post(
        'https://api.statementai.com/api/auth/login/2fa/',
        json={
            'challenge_id': challenge_id,
            'recovery_code': recovery_code
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data['access_token']
    elif response.status_code == 400:
        error = response.json()
        if 'Invalid recovery code' in error['detail']:
            print("Recovery code is invalid or already used")
        return None
```

### Batch Operations on Statements

```bash
# List all statements with pagination
function get_all_statements() {
  local page=1
  local all_statements=()
  
  while true; do
    response=$(curl -s -X GET \
      "https://api.statementai.com/api/statements/?page=$page&limit=100" \
      -H "Authorization: Bearer $TOKEN")
    
    # Parse JSON and add to array
    statements=$(echo $response | jq '.results[]')
    all_statements+=($statements)
    
    # Check if more pages
    total_pages=$(echo $response | jq '.pagination.total_pages')
    if [ $page -ge $total_pages ]; then
      break
    fi
    page=$((page + 1))
  done
  
  echo $all_statements
}
```

### Webhook-like Polling Pattern

For real-time updates on statement processing:

```javascript
async function waitForStatementProcessing(statementId, maxWaitSeconds = 300) {
  const startTime = Date.now();
  const maxWait = maxWaitSeconds * 1000;
  const pollIntervalMs = 2000; // Poll every 2 seconds
  
  while (Date.now() - startTime < maxWait) {
    const response = await fetch(
      `https://api.statementai.com/api/statements/${statementId}/status/`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const status = await response.json();
    
    if (status.processing_status === 'completed') {
      return status;
    }
    
    if (status.processing_status === 'failed') {
      throw new Error(`Processing failed: ${status.error}`);
    }
    
    // Show progress to user
    console.log(`Progress: ${status.progress}%`);
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
  }
  
  throw new Error('Processing timeout');
}
```

---

## Best Practices

1. **Always use HTTPS** in production for all API calls
2. **Store tokens securely** - don't log them or include in URLs
3. **Implement token refresh** before expiration to avoid auth failures
4. **Use pagination** for endpoints that return lists to handle large datasets
5. **Handle rate limits gracefully** with exponential backoff and jitter
6. **Validate input** before sending to API to catch errors early
7. **Check error responses** and handle specific error codes appropriately
8. **Save recovery codes immediately** after enabling 2FA
9. **Use descriptive recovery code message** - remind users this is their only backup
10. **Implement timeouts** on API requests (default 30 seconds recommended)

---

## Support & Contact

For API issues, bugs, or feature requests:

- **Email**: api-support@statementai.com
- **GitHub Issues**: https://github.com/statement-ai/api/issues
- **Slack Community**: [Link to Slack workspace]

---

**API Version**: 1.0.0  
**Last Updated**: November 8, 2024  
**Status**: Stable
