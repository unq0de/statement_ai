---
layout: page
title: Security and Privacy
permalink: /security/
---

# Security and privacy

This project handles financial data, so access control and retention are important parts of the design.

## Data isolation

Every `BankStatement` is linked to a single Django user. The API views filter by `user=self.request.user` or by the statement owner before returning data. This prevents one user from reading or deleting another user's statements or transactions.

## Authentication and authorization

The project uses JWT authentication for protected endpoints. Requests without a valid token are rejected with `401 Unauthorized`.

The system also uses access checks on file downloads and statement detail operations. For example, the original PDF file is only served if the current user owns the statement.

## Optional two-factor authentication

Users can optionally enroll in TOTP with an authenticator app. Setup requires the current password and a code from the app before 2FA is enabled. TOTP secrets are encrypted at rest; set a stable `TWO_FACTOR_ENCRYPTION_KEY` in production. If it is omitted, the encryption key is derived from `SECRET_KEY`, so rotating `SECRET_KEY` will require enrolled users to set up 2FA again.

Password login for an enrolled user returns a five-minute, single-use challenge instead of JWTs. A valid TOTP or one-time recovery code is required before the API issues tokens. Recovery codes are stored as keyed hashes and can only be used once. TOTP time windows are checked for replay, and enabling or disabling 2FA revokes earlier JWTs through an authentication-version claim. The user must sign in again after either change.

`TWO_FACTOR_ENABLED=0` disables the feature globally. The default is enabled, but users remain on password-only login until they enroll. Setup, disable, recovery-code regeneration, and challenge verification are rate-limited and audited. The API does not provide the QR-code UI; the external client should render `otpauth_url` and display recovery codes only once.

## Rate limiting

Every request under `/api/` is rate-limited before authentication and permission checks. Global and endpoint quotas use atomic fixed-window counters in the configured cache. Anonymous requests are keyed by client IP; requests with a valid, unexpired access token are keyed by user ID. Failed-login counters expire 15 minutes after the first failure for that IP/username pair.

| Request | Limit | Key |
| --- | --- | --- |
| Anonymous API request | 60 per minute | Client IP |
| Authenticated API request | 120 per minute | User ID |
| `POST /api/auth/register/` | 5 per hour | Client IP |
| `POST /api/auth/login/` | 10 per minute | Client IP |
| `POST /api/auth/login/2fa/` | 10 per hour | Client IP |
| 2FA setup, enable, disable, and recovery-code replacement | 10 per hour | User ID |
| `POST /api/auth/password-reset/` | 5 per hour | Client IP |
| Password reset email address | 3 per hour | Normalized email address |
| `POST /api/auth/password-reset/confirm/` | 10 per hour | Client IP |
| Failed logins | 5 per 15 minutes | Client IP and normalized username |
| `POST /api/statements/upload/` | 5 per hour | User ID |

A successful login clears that IP/username pair's failed-login counter. The username is HMAC-hashed before it is stored in the cache. Limit responses return `429 Too Many Requests`, an `error` field, and a `Retry-After` header with the seconds remaining in the current window.

Docker Compose starts a shared Redis cache for the web and cron services. `REDIS_URL` is required when `DEBUG=0`; without it, startup fails instead of silently using a per-process cache. Redis is configured without key eviction so memory pressure cannot silently reset limits. Monitor Redis memory and capacity; if the cache is unavailable, API requests fail rather than bypassing the limits.

`NUM_PROXIES` defaults to `0`, which uses the connection's remote address and ignores `X-Forwarded-For`. If the app is behind a trusted reverse proxy, set it to the exact number of trusted proxy hops and ensure that proxy strips any client-supplied forwarding headers before setting its own. Do not expose the app directly when trusting forwarded addresses.

## Passwords and recovery

Passwords must be at least 12 characters long. Django also rejects common passwords, passwords too similar to account details, and passwords consisting only of numbers. There is no mandatory character-class mix, so long passphrases remain valid.

At login, accounts whose correct password no longer meets these requirements are directed to the reset flow before receiving JWTs. This also applies the policy to existing accounts without exposing account state to unauthenticated callers.

Password recovery uses `POST /api/auth/password-reset/` and `POST /api/auth/password-reset/confirm/`. Requests for unknown email addresses receive the same response as valid requests. Reset tokens expire after one hour by default, are single-use, and are checked again under a database row lock before the password changes. A successful reset invalidates existing JWTs.

In development, reset emails are written to the application console. Production deployments must configure `EMAIL_HOST`, `DEFAULT_FROM_EMAIL`, TLS or SSL, and an HTTPS `PASSWORD_RESET_URL` pointing to the client page that collects the new password. SMTP authentication can be configured through `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`. `PASSWORD_RESET_TIMEOUT` controls token lifetime in seconds. Reset credentials are placed in the URL fragment so browsers do not send them in HTTP requests or referrer headers.

## File handling

Uploaded PDFs are stored in the local media directory and tied to the owning user. They are not exposed through a public static route in production. Instead, the application serves the file through the authenticated API route.

## Personal data export

The export endpoint returns the user's own data as JSON. This is intended to support access and portability workflows for personal financial information.

## Account deletion

Deleting an account is not a soft delete. The API confirms the password and then removes the user record. Related statements, transactions, and uploaded files are deleted as part of the cascade.

## Data retention

The project includes automatic data retention through the `delete_expired_data` management command. The `DATA_RETENTION_DAYS` environment variable controls how long statement records remain eligible for cleanup.

This is a practical safeguard that helps reduce long-term storage of old banking data.

## Security recommendations

For production usage, you should:

- keep `SECRET_KEY` in a secure environment variable
- rotate the Gemini API key if it is exposed
- use `DEBUG=0` in production
- set explicit `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`
- protect the database and media directory with the same access controls as the rest of the app

## Related pages

- [Features]({{ '/features/' | relative_url }})
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }})
- [API reference]({{ '/api-reference/' | relative_url }})
