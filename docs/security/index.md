---
layout: page
title: Security and Privacy
permalink: /security/
---

# Security and privacy

This project handles financial data, so access control and retention are central to the design. This page describes what the code actually does. It is not a compliance statement or legal advice.

## What is stored, and where

| Data | Location | Notes |
| --- | --- | --- |
| Users and passwords | PostgreSQL | Django's default password hashing. |
| Statements, transactions, AI evaluations | PostgreSQL | Plain text columns. The application adds no field-level encryption. |
| Uploaded PDFs | `media/` volume (`media_data` in Compose) | Stored unencrypted by the application under `statements/YYYY/MM/`. |
| TOTP secrets | PostgreSQL | Encrypted with Fernet using `TWO_FACTOR_ENCRYPTION_KEY`. |
| Recovery codes and login challenges | PostgreSQL | Only hashes are stored: HMAC-SHA256 for recovery codes, SHA-256 for challenges. |
| API usage, Gemini usage, audit events | PostgreSQL | No request bodies, query strings, IP addresses or PDF content. |
| Rate-limit and failed-login counters | Redis cache | Keyed by HMAC digests, not by raw IP addresses, usernames or emails. |

Encryption of the database and of the media volume at rest is up to your infrastructure.

## Data isolation

Every `BankStatement` belongs to one Django user, and every `Transaction` belongs to a statement. The API views filter by the authenticated user before returning or deleting anything. Requesting someone else's statement or transaction returns `404`, the same as a missing one.

## Authentication and authorization

Every endpoint requires a valid JWT unless it is explicitly public (registration, confirmation, resend, login, 2FA login, refresh, password reset). A missing or invalid token returns `401 Unauthorized`.

Tokens can be revoked. A password change or reset invalidates all existing tokens, and enabling or disabling 2FA does too, through an `auth_version` claim that is checked on every request. The refresh endpoint applies the same checks and also refuses inactive or deleted users.

New accounts are inactive until the email address is confirmed. Registration, confirmation links and password-reset links use Django's token generator, are single-use, and expire after `PASSWORD_RESET_TIMEOUT` seconds (one hour by default). Their `uid` and `token` travel in the URL fragment, so browsers do not send them in HTTP requests or referrer headers.

Password confirmation is required to delete an account and to start, disable or re-key two-factor authentication.

## Optional two-factor authentication

Users can enroll in TOTP with an authenticator app. Enrollment needs the account password and a code from the app. TOTP secrets are encrypted at rest. Set a stable `TWO_FACTOR_ENCRYPTION_KEY` in production: if it is omitted, the key is derived from `SECRET_KEY`, and rotating `SECRET_KEY` would make enrolled devices unusable.

For an enrolled user, a correct password returns a single-use challenge (five minutes by default) instead of tokens. A TOTP code or an unused recovery code is required to complete the login. Details:

- TOTP codes are accepted within one 30-second step either side of the current one, and a code that has been used once is never accepted again.
- A challenge is burned after `TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS` wrong codes.
- Recovery codes are stored as keyed hashes and work once. Because the hash uses `SECRET_KEY`, rotating it invalidates existing recovery codes.
- Setup, disable, recovery-code replacement and challenge verification are rate-limited and audited.

`TWO_FACTOR_ENABLED=0` turns the feature off for the whole deployment. By default it is on, and users stay on password-only login until they enroll. The API does not render QR codes; the client should render `otpauth_url` and show recovery codes only once.

## Passwords

The default policy requires at least 12 characters, rejects common passwords, rejects passwords too similar to the username or email, rejects all-numeric passwords, and requires at least one punctuation mark or symbol. Every rule except the minimum length can be switched off, and the length is configurable. See [Configuration]({{ '/configuration/' | relative_url }}).

At login, an account whose correct password no longer satisfies the policy is refused tokens and told to reset it. That message is only returned after the correct password was supplied, so it reveals nothing to someone guessing credentials.

Password-reset requests and confirmation-resend requests return the same response whether or not an account matches the address. The reset token is checked again under a database row lock before the password changes.

## Rate limiting

Every request under `/api/` is rate-limited before authentication and permission checks. Global and per-endpoint quotas use atomic fixed-window counters in the Django cache. Requests carrying a valid, unexpired access token are counted per user; all others per IP address. Failed logins are counted per IP address and username, and five failures trigger a 15-minute cooldown. A successful login clears the counter. The username is hashed before it enters the cache.

The complete table is on the [Configuration]({{ '/configuration/#rate-limits' | relative_url }}) page.

Operational notes:

- `REDIS_URL` is required when `DEBUG=0`. Without it, startup fails instead of silently using a per-process cache.
- Compose runs Redis without key eviction (`noeviction`), so memory pressure cannot silently reset counters. Monitor its memory use. If the cache is unreachable, requests fail rather than bypassing the limits.
- `NUM_PROXIES` defaults to `0`: the connection's remote address is used and `X-Forwarded-For` is ignored. Behind a trusted reverse proxy, set it to the exact number of trusted proxy hops, and make sure the proxy removes client-supplied forwarding headers. Do not expose the application directly while trusting forwarded addresses.

## File handling

Uploads are checked for content type, file signature and size before they are stored. PDFs are saved in the media directory and tied to the owner. Django serves `/media/` only when `DEBUG=1`; in production the authenticated download endpoint is the only way to retrieve a file, and it checks ownership.

## Input validation and Gemini output

Request bodies are validated by DRF serializers. The Gemini reply is parsed as JSON, but its values are not checked beyond that: categories and transaction types are not compared with the allowed lists, and a transaction without a valid date makes the processing attempt fail.

## Third-party data transfer

Every uploaded PDF is sent in full to the Google Gemini API. Whoever operates the service for real users is responsible for a legal basis, a data processing agreement with Google, and a Gemini plan whose data-use terms fit the data. Google's terms differ between paid and free usage; read the [Gemini API Additional Terms of Service](https://ai.google.dev/gemini-api/terms) instead of relying on a summary here. As a rule, do not use a free-tier key with real financial data.

## Audit log and usage records

`AuditEvent` rows record, among other things: registration and confirmation; login success, failure, weak-password rejection and 2FA challenges; 2FA setup, enable, disable and failures; password-reset requests and completion; uploads accepted or refused by the monthly limit; processing started, completed, failed or not queued; statement deletion and bulk deletion; file downloads; data exports; account deletion; and rate-limit hits.

In Django admin, audit events cannot be added, changed or deleted by hand. API usage and Gemini usage records can be browsed and filtered but not added or edited. Usage tracking can be turned off with `API_USAGE_TRACKING_ENABLED=0`; audit events are always recorded.

## Retention and erasure

The cleanup command `delete_expired_data` runs daily in the `cron` container. It deletes:

| What | When |
| --- | --- |
| Bank statements, with their PDFs and transactions | older than `DATA_RETENTION_DAYS`, measured from `uploaded_at` |
| API usage records and Gemini usage records | older than `API_USAGE_RETENTION_DAYS` |
| Audit events | older than `AUDIT_LOG_RETENTION_DAYS` |
| 2FA login challenges | expired |

> `.env.example` sets `DATA_RETENTION_DAYS=1`. With that value, statements are deleted a day after upload. Change it deliberately.

Users can also erase data themselves. `DELETE /api/statements/<id>/` and `/api/statements/delete-all/` remove statements, and `DELETE /api/auth/account/` removes the user, statements, transactions and PDFs. Account deletion is a hard delete, not a soft delete. Usage records and audit events survive it with the user reference set to null.

`GET /api/auth/export/` returns the user's profile and statements as JSON, which supports access and portability requests. It does not include usage records, audit events or 2FA data.

## Known limitations

- The Compose setup runs Django's development server. The repository does not include a production WSGI server.
- Compose publishes PostgreSQL on host port `5432`.
- Statements, transactions and PDFs are not encrypted by the application.
- Error responses use more than one JSON shape.
- There is no duplicate detection, and no way to re-run a failed statement other than uploading it again.

## Recommendations for production

- Keep `SECRET_KEY` and `TWO_FACTOR_ENCRYPTION_KEY` in a secret store and never commit `.env`.
- Rotate the Gemini API key if it may have been exposed.
- Use `DEBUG=0` and set explicit `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`.
- Terminate TLS in front of the application and set `NUM_PROXIES` to match.
- Do not expose PostgreSQL or the media volume publicly, and back both up.
- Review the [Deployment]({{ '/deployment/' | relative_url }}) page before going live.

## Related pages

- [Features]({{ '/features/' | relative_url }})
- [Configuration]({{ '/configuration/' | relative_url }})
- [Deployment]({{ '/deployment/' | relative_url }})
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }})
