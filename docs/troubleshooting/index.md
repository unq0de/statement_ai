---
layout: page
title: Troubleshooting
permalink: /troubleshooting/
---

# Troubleshooting

These are the problems you are most likely to meet while setting up and using the project, with causes that follow from the code and configuration.

## Docker Compose fails to start

Check that Docker is running and that ports `8001` and `5432` are free. Then look at the services:

```bash
docker compose ps
docker compose logs migrate
docker compose logs web
docker compose logs worker
docker compose logs redis
docker compose logs db
docker compose logs cron
```

`web`, `worker` and `cron` wait for the `migrate` service to finish successfully. If a migration fails or the database is unreachable, they stay down, so start with `docker compose logs migrate`.

## The web container exits right after starting

With `DEBUG=0`, startup stops with a `RuntimeError` that names the missing setting. The possible causes are a missing `SECRET_KEY`, `GEMINI_API_KEY` or `REDIS_URL`, a missing `EMAIL_HOST`, a default `DEFAULT_FROM_EMAIL`, no TLS or SSL for email, or link URLs that are not absolute HTTPS URLs. The full list is on the [Configuration]({{ '/configuration/#production-checks' | relative_url }}) page.

Compose passes `DEBUG` without a default. If it is missing from `.env`, the application starts in production mode and trips over these checks. Set `DEBUG=1` for local work.

## Every request returns 400 "Invalid HTTP_HOST header"

`DEBUG=0` with an empty `ALLOWED_HOSTS`. Set it to the hostnames clients use, for example `localhost,127.0.0.1`.

## Database connection issues

The containers always connect to the local database as host `db` on port `5432`; Compose sets those values itself, so `POSTGRES_HOST` and `POSTGRES_PORT` in `.env` have no effect inside Compose. Check `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PASSWORD`, and look at `docker compose logs db`.

If you changed the database credentials after the `postgres_data` volume had been created, the database keeps the old ones. Either change them back, or remove the volume (this deletes the data).

Outside Docker, the default `POSTGRES_HOST` is `db`, which only exists inside Compose. Set it to `localhost` or your database host.

## The API returns 401

A `401` means the token is missing, expired or revoked. Send `Authorization: Bearer <access_token>`, refresh the token or log in again. For a login that returns `401` with a correct password, there are three common reasons:

- The account has not been confirmed yet. Use the link from the confirmation email, or request a new one.
- The password no longer meets the current policy, and the error message says to reset it.
- You just changed the password, or enabled or disabled 2FA. Older tokens are revoked on purpose, so log in again.

## No confirmation or reset email arrives

With `DEBUG=1`, emails are printed to the web log, not sent: `docker compose logs web | tail -n 40`. In production, check the SMTP settings. Sending failures are logged but not reported to the client, so the API still answers `201` or `200`. If the link in the email is unusable, check `REGISTRATION_CONFIRMATION_URL` and `PASSWORD_RESET_URL`.

## Upload returns 400

The part must be called `file` or `document`, contain a real PDF, and be at most 10 MB. The exact messages and the order of the checks are on the [Statement endpoints]({{ '/api-reference/statements/' | relative_url }}) page. Common causes are a file that is not a PDF, a corrupted or empty file, or an unsupported declared content type.

## Upload returns 429

Either more than five uploads in an hour, or `GEMINI_MONTHLY_LIMIT_PER_USER` has been reached. The body tells them apart: the monthly limit includes `limit` and `used`. Both responses have a `Retry-After` header.

## Upload returns 503

The file could not be stored or the job could not be queued. The second case usually means Redis is down or `CELERY_BROKER_URL` is wrong. The statement is kept with status `failed`. Fix the cause and upload the file again.

## A statement stays `pending`

The job is queued but no worker has picked it up. Check that the `worker` container is running and that it can reach Redis:

```bash
docker compose ps
docker compose logs worker
```

Also check that `CELERY_BROKER_URL` points to the Redis service.

## A statement ends up `failed`

Processing is asynchronous, so failures show up as a `failed` status, not as an error on the upload request. After three retries, the status becomes `failed` and the API only shows a generic message. The real reason is in the worker log:

```bash
docker compose logs worker
```

Typical causes are a missing or invalid `GEMINI_API_KEY`, a PDF that Gemini cannot read, a reply that is not valid JSON, or a transaction without a usable date. The Gemini usage record in Django admin shows the exception class in `error_type`. There is no retry endpoint; upload the file again.

## Statements disappear

The nightly cleanup deletes statements older than `DATA_RETENTION_DAYS`. `.env.example` sets that to `1`. Raise it and restore from backups if you have them; deleted statements cannot be recovered.

## Statements are missing from a list

The API only returns statements that belong to the authenticated user. Check that you are using the right account and that no `processed` filter hides unfinished statements. Statements that are still processing or have failed have no transactions yet.

## Rate limits seem wrong

Counters live in the Django cache. Without `REDIS_URL` the cache is per process, so limits are not shared. Behind a reverse proxy, a wrong `NUM_PROXIES` makes every client look like the proxy's IP address, and one busy client can lock out all others. See the [Configuration]({{ '/configuration/#rate-limits' | relative_url }}) page.

## Two-factor codes stop working

If `TWO_FACTOR_ENCRYPTION_KEY` was not set, the encryption key was derived from `SECRET_KEY`, and changing `SECRET_KEY` makes enrolled authenticator setups unusable. Recovery codes are hashed with `SECRET_KEY` as well. Set the key explicitly before enrolling users. Authenticator codes also depend on the clock; check that the server and the phone are in sync.

## Cleaning old data manually

```bash
docker compose exec cron python manage.py delete_expired_data
```

The command also works on the `web` container.

## Related pages

- [Installation]({{ '/installation/' | relative_url }})
- [Configuration]({{ '/configuration/' | relative_url }})
- [Features]({{ '/features/' | relative_url }})
- [API reference]({{ '/api-reference/' | relative_url }})
