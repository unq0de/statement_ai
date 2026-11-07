---
layout: page
title: Installation
permalink: /installation/
---

# Installation and setup

This project is meant to run locally with Docker, but the application is still a standard Django project. The setup is straightforward if you follow the environment variables and service layout from the repository.

## Requirements

- Python 3.11
- Docker and Docker Compose
- PostgreSQL credentials or the default local database container
- Google Gemini API key

## 1. Clone the repository

```bash
git clone https://github.com/unq0de/statement_ai.git
cd statement_ai
```

## 2. Configure the environment

```bash
cp .env.example .env
```

Edit `.env` and set the values you need. A minimal production-style example looks like this:

```dotenv
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=1
GEMINI_API_KEY=your-gemini-api-key
API_USAGE_TRACKING_ENABLED=1
API_USAGE_RETENTION_DAYS=90
AUDIT_LOG_RETENTION_DAYS=365
GEMINI_MONTHLY_LIMIT_PER_USER=0
DATA_RETENTION_DAYS=365
DB_ENGINE=local
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=statement_ai_db
POSTGRES_USER=statement_ai_user
POSTGRES_PASSWORD=Test123!
ALLOWED_HOSTS=
CORS_ALLOWED_ORIGINS=
REDIS_URL=redis://redis:6379/1
CELERY_BROKER_URL=redis://redis:6379/0
NUM_PROXIES=0
PASSWORD_MIN_LENGTH=12
PASSWORD_CHECK_USER_ATTRIBUTES=1
PASSWORD_CHECK_COMMON=1
PASSWORD_CHECK_NUMERIC=1
PASSWORD_CHECK_SPECIAL_CHARACTERS=1
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=1
EMAIL_USE_SSL=0
EMAIL_USE_HTML_TEMPLATES=0
DEFAULT_FROM_EMAIL=Statement AI <no-reply@example.com>
PASSWORD_RESET_TIMEOUT=3600
PASSWORD_RESET_URL=https://app.example.com/reset-password/
REGISTRATION_CONFIRMATION_URL=https://app.example.com/confirm-email/
TWO_FACTOR_ENABLED=1
TWO_FACTOR_ISSUER=Statement AI
TWO_FACTOR_ENCRYPTION_KEY=
TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS=300
TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS=5
TWO_FACTOR_RECOVERY_CODE_COUNT=10
```

## 3. Database configuration

The project supports two database modes:

### Local PostgreSQL container

This is the default behavior. Docker Compose starts a PostgreSQL service named `db` for the project.

```dotenv
DB_ENGINE=local
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=statement_ai_db
POSTGRES_USER=statement_ai_user
POSTGRES_PASSWORD=statement_ai_password
```

### Hosted Supabase database

If you want to use Supabase instead of the local container, set `DB_ENGINE=supabase` and provide the Supabase connection values:

```dotenv
DB_ENGINE=supabase
SUPABASE_DB_HOST=db.xxxxxx.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_SSLMODE=require
```

## 4. Start the services

```bash
docker compose up -d --build
```

This starts the web, Celery worker, and cron containers, the PostgreSQL database, and Redis. A one-off `migrate` service waits for the database and applies pending migrations before the web, worker, and cron services start. If migration fails, those services remain stopped. Redis database 0 is the Celery broker (`CELERY_BROKER_URL`); database 1 is used by Django for cache and shared rate limits (`REDIS_URL`). Production deployments with `DEBUG=0` must configure both URLs to reachable Redis databases.

Password reset and registration confirmation require working SMTP settings and client pages at `PASSWORD_RESET_URL` and `REGISTRATION_CONFIRMATION_URL`. Set `EMAIL_USE_HTML_TEMPLATES=1` to include HTML email versions; set it to `0` to send plain text only. Both formats use editable templates under `templates/emails/`. In development, the console email backend prints these messages in the web container logs. Set `PASSWORD_MIN_LENGTH` to change the required minimum password length; set each `PASSWORD_CHECK_*` value to `0` to disable that validator.

API usage tracking is enabled by default. It records API route, method, response status, duration, and request size without storing request bodies, query strings, or client IP addresses. Set `API_USAGE_TRACKING_ENABLED=0` to disable event logging. `API_USAGE_RETENTION_DAYS` controls how long usage records are retained; the daily cleanup job removes expired records. `GEMINI_MONTHLY_LIMIT_PER_USER=0` allows unlimited statement submissions; a positive value caps each account's submissions per calendar month. Usage records and Gemini token totals are available in Django admin. The separate audit log records security and data-changing actions and is read-only in admin; `AUDIT_LOG_RETENTION_DAYS` controls its retention period.

Optional per-user TOTP two-factor authentication is enabled globally by default. Set `TWO_FACTOR_ENABLED=0` to disable it for the deployment. Set a stable `TWO_FACTOR_ENCRYPTION_KEY` in production; generate one with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. The key must remain stable or enrolled users will need to set up 2FA again.

## 5. Optional admin user

```bash
docker compose exec web python manage.py createsuperuser
```

## 6. Access the application

The API is available at:

```text
http://localhost:8001/api/
```

The Django admin is available at:

```text
http://localhost:8001/admin/
```

## 8. Verify the deployment

A quick check is to hit the login endpoint or query the statement routes with an authenticated request.

```bash
curl -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"StrongPass123!"}'
```

If the call succeeds, the project is running correctly.

## Runtime notes

- The `web` service runs `manage.py runserver 0.0.0.0:8001`.
- The `cron` service executes the retention cleanup script on a schedule defined in `cron/statement-ai-cron`.
- Uploaded PDFs are stored under `media/` and remain tied to the uploading user.

## Related pages

- [Getting started]({{ '/getting-started/' | relative_url }})
- [Features]({{ '/features/' | relative_url }})
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }})
