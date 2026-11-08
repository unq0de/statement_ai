---
layout: page
title: Configuration
permalink: /configuration/
---

# Configuration

All configuration comes from environment variables, read in `statement_ai/settings.py`. With Docker Compose, put them in `.env`; Compose forwards them to the `web`, `migrate`, `worker` and `cron` containers. `.env.example` lists most of them with starting values. Never commit `.env`, and rotate `SECRET_KEY` and `GEMINI_API_KEY` if they are ever exposed.

Boolean settings accept `1`, `true`, `yes` or `on` (case-insensitive) as true. Anything else is false.

## Core

| Variable | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | none | Django secret key. Required when `DEBUG` is off. It also keys the HMACs behind recovery codes and rate-limit identities, so rotating it invalidates existing recovery codes. |
| `DEBUG` | `0` | `1` is development mode: every host and CORS origin is allowed, emails go to the console, and Django serves `/media/`. Compose passes `DEBUG` without a default, so set it explicitly. |
| `GEMINI_API_KEY` | none | Required when `DEBUG` is off. Processing fails without it. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Gemini model used for statement extraction. |
| `ALLOWED_HOSTS` | empty | Comma-separated hostnames. Only read when `DEBUG=0`. An empty value makes Django reject every request. |
| `CORS_ALLOWED_ORIGINS` | empty | Comma-separated origins. Only read when `DEBUG=0`. |
| `NUM_PROXIES` | `0` | Number of trusted reverse proxies in front of the API. At `0` the connection's remote address is used and `X-Forwarded-For` is ignored. |
| `DATA_RETENTION_DAYS` | `365` | Statements older than this are deleted by the cleanup command. `.env.example` sets `1`. |

## Redis and Celery

| Variable | Default | Description |
| --- | --- | --- |
| `REDIS_URL` | none (Compose: `redis://redis:6379/1`) | Django cache, used for rate limits and failed-login counters. Required when `DEBUG=0`. If unset in development, an in-process cache is used. |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker. |

## Web server

The `web` container runs gunicorn. These variables are read by Docker Compose and the container start command, not by `statement_ai/settings.py`:

| Variable | Default | Description |
| --- | --- | --- |
| `GUNICORN_WORKERS` | `3` | Number of gunicorn worker processes. |
| `GUNICORN_TIMEOUT` | `60` | Worker timeout in seconds. |
| `GUNICORN_EXTRA_ARGS` | empty | Additional gunicorn arguments, e.g. `--reload` during development (the `.env.example` value). |

## Database

| Variable | Default | Description |
| --- | --- | --- |
| `DB_ENGINE` | `local` | `local` uses the Compose `db` container. `supabase` uses a hosted Supabase database. |
| `POSTGRES_HOST` | `db` | Used only for `DB_ENGINE=local`. Compose sets `db` for the containers regardless, so this matters only outside Compose. |
| `POSTGRES_PORT` | `5432` | As above. |
| `POSTGRES_DB` | `statement_ai_db` | Database name. Also used to initialize the `db` container. |
| `POSTGRES_USER` | `statement_ai_user` | Database user. |
| `POSTGRES_PASSWORD` | `statement_ai_password` | Database password. Change it. |
| `SUPABASE_DB_HOST` | none | Required with `DB_ENGINE=supabase` when `DEBUG=0`. |
| `SUPABASE_DB_PORT` | `5432` | `5432` direct, `6543` for the transaction pooler. |
| `SUPABASE_DB_NAME` | `postgres` | |
| `SUPABASE_DB_USER` | none | Required with `DB_ENGINE=supabase` when `DEBUG=0`. |
| `SUPABASE_DB_PASSWORD` | none | Required with `DB_ENGINE=supabase` when `DEBUG=0`. |
| `SUPABASE_DB_SSLMODE` | `require` | |
| `SUPABASE_DB_CONN_MAX_AGE` | `60` | Read by `settings.py`, but neither forwarded by `docker-compose.yml` nor listed in `.env.example`. Add it to the Compose environment to change it. |

## Authentication and passwords

| Variable | Default | Description |
| --- | --- | --- |
| `PASSWORD_MIN_LENGTH` | `12` | Minimum password length. |
| `PASSWORD_CHECK_USER_ATTRIBUTES` | `1` | Reject passwords too similar to the username or email. |
| `PASSWORD_CHECK_COMMON` | `1` | Reject passwords on Django's common-password list. |
| `PASSWORD_CHECK_NUMERIC` | `1` | Reject all-numeric passwords. |
| `PASSWORD_CHECK_SPECIAL_CHARACTERS` | `1` | Require at least one punctuation mark or symbol. |
| `TWO_FACTOR_ENABLED` | `1` | Set to `0` to turn the 2FA feature off. Its endpoints then return `404` and login never issues a challenge. |
| `TWO_FACTOR_ISSUER` | `Statement AI` | Issuer name shown in authenticator apps. |
| `TWO_FACTOR_ENCRYPTION_KEY` | derived from `SECRET_KEY` | Fernet key that encrypts TOTP secrets. Set it explicitly and keep it stable. |
| `TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS` | `300` | Lifetime of a login challenge, minimum `30`. The setup window is twice this value. |
| `TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS` | `5` | Wrong codes allowed per challenge, minimum `1`. |
| `TWO_FACTOR_RECOVERY_CODE_COUNT` | `10` | Recovery codes created per enrollment, minimum `1`. |

Generate a Fernet key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If you leave `TWO_FACTOR_ENCRYPTION_KEY` empty, the key is derived from `SECRET_KEY`, and rotating `SECRET_KEY` later makes enrolled authenticator devices unusable.

## Email

| Variable | Default | Description |
| --- | --- | --- |
| `EMAIL_BACKEND` | console in development, SMTP otherwise | Overrides the Django email backend. |
| `EMAIL_HOST` | empty | SMTP host. Required when `DEBUG=0`. |
| `EMAIL_PORT` | `587` | |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | empty | SMTP credentials. |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL` | off | Enable exactly one. One is required when `DEBUG=0`; enabling both stops startup. |
| `EMAIL_TIMEOUT` | `10` | Seconds. |
| `EMAIL_USE_HTML_TEMPLATES` | `0` | `1` sends HTML emails from `templates/emails/` in addition to the plain-text version. |
| `DEFAULT_FROM_EMAIL` | `webmaster@localhost` | Must be changed when `DEBUG=0`. |
| `PASSWORD_RESET_URL` | `http://localhost:3000/reset-password/` in development | Your client page for resetting passwords. `uid` and `token` are added to its URL fragment. Must be an absolute HTTPS URL when `DEBUG=0`. |
| `REGISTRATION_CONFIRMATION_URL` | `http://localhost:3000/confirm-email/` in development | The same, for email confirmation. |
| `PASSWORD_RESET_TIMEOUT` | `3600` | Lifetime in seconds of reset and confirmation links. Both use Django's token generator. |

## Usage tracking, audit and limits

| Variable | Default | Description |
| --- | --- | --- |
| `API_USAGE_TRACKING_ENABLED` | `1` | Record API and Gemini usage. |
| `API_USAGE_RETENTION_DAYS` | `90` | Retention for API and Gemini usage records, minimum `1`. |
| `AUDIT_LOG_RETENTION_DAYS` | `365` | Retention for audit events, minimum `1`. |
| `GEMINI_MONTHLY_LIMIT_PER_USER` | `0` | Statements one user may submit per calendar month. `0` means no limit. Negative values stop startup. |

## Production checks

With `DEBUG=0`, `settings.py` refuses to start unless all of the following hold:

- `SECRET_KEY` is set and is not the built-in fallback value.
- `GEMINI_API_KEY` is set.
- `REDIS_URL` is set.
- `EMAIL_HOST` is set and `DEFAULT_FROM_EMAIL` is not `webmaster@localhost`.
- `EMAIL_USE_TLS` or `EMAIL_USE_SSL` is enabled.
- `PASSWORD_RESET_URL` and `REGISTRATION_CONFIRMATION_URL` are absolute HTTPS URLs.
- With `DB_ENGINE=supabase`, host, user and password are set.

`ALLOWED_HOSTS` is not checked at startup, but an empty value means Django answers every request with `400`.

## Rate limits

The limits are constants in `settings.py` (`API_RATE_LIMITS`), not environment variables. They use fixed time windows. Exceeded limits return `429 Too Many Requests` with a `Retry-After` header.

| Scope | Limit | Keyed by |
| --- | --- | --- |
| Anonymous requests, all endpoints | 60 per minute | IP address |
| Authenticated requests, all endpoints | 120 per minute | User |
| `POST /api/auth/login/` | 10 per minute | IP address |
| Failed login with the same IP and username | 5 failures, then a 15-minute cooldown | IP address and username |
| `POST /api/auth/register/` | 5 per hour | IP address |
| Registration confirm and resend | 10 per hour | IP address |
| Confirmation emails | 3 per hour | Email address |
| `POST /api/auth/password-reset/` | 5 per hour | IP address |
| Password-reset emails | 3 per hour | Email address |
| `POST /api/auth/password-reset/confirm/` | 10 per hour | IP address |
| `POST /api/auth/login/2fa/` | 10 per hour | IP address |
| 2FA setup, enable, disable, recovery codes | 10 per hour | User |
| `POST /api/statements/upload/` | 5 per hour | User |

Requests are attributed to a user only when they carry a valid, unexpired access token; otherwise the IP address is used. The counters live in the Django cache, so they are shared between processes only when `REDIS_URL` is set. Behind a reverse proxy, set `NUM_PROXIES` correctly, or every client appears to have the proxy's IP address.

## Hard-coded values

These are not configurable through the environment:

| Value | Where |
| --- | --- |
| Maximum upload size of 10 MB | `statements/views.py` |
| Access token lifetime of 60 minutes, refresh token lifetime of 1 day | `SIMPLE_JWT` in `settings.py` |
| Processing retries: 3, with exponential backoff and jitter | `statements/tasks.py` |
| Worker concurrency of 2 | `docker-compose.yml` |
| Cleanup schedule at 03:00 UTC | `cron/statement-ai-cron` |

## Related pages

- [Installation]({{ '/installation/' | relative_url }})
- [Deployment]({{ '/deployment/' | relative_url }})
- [Security]({{ '/security/' | relative_url }})
