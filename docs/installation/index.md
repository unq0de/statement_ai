---
layout: page
title: Installation
permalink: /installation/
---

# Installation and setup

The project is built to run with Docker Compose. This page covers the supported Docker setup, the two database options and how to verify the result. Every environment variable is described on the [Configuration]({{ '/configuration/' | relative_url }}) page. Production topics are on the [Deployment]({{ '/deployment/' | relative_url }}) page.

## Requirements

- Docker and Docker Compose
- A Google Gemini API key
- An SMTP server, only if you run with `DEBUG=0`. In development, emails are printed to the web container log.

Python 3.11 is only needed if you run the project outside Docker; the image already contains it.

## 1. Clone the repository

```bash
git clone https://github.com/unq0de/statement_ai.git
cd statement_ai
```

## 2. Create the environment file

```bash
cp .env.example .env
```

At a minimum set `SECRET_KEY` and `GEMINI_API_KEY`. Review these as well:

- `DATA_RETENTION_DAYS`: `.env.example` sets `1`. Any statement older than that is deleted by the nightly cleanup job. The application default is `365`.
- `POSTGRES_PASSWORD`: the example value is only suitable for local use.
- `DEBUG`: Compose passes it through without a default. Set it explicitly to `1` for development or `0` for production.

A short development configuration looks like this:

```dotenv
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=1
GEMINI_API_KEY=your-gemini-api-key
DATA_RETENTION_DAYS=365
DB_ENGINE=local
```

`.env.example` contains the complete list with sensible defaults. Never commit `.env`.

## 3. Choose a database

### Local PostgreSQL container (default)

With `DB_ENGINE=local`, Compose runs a `postgres:15-alpine` service named `db`. The containers always connect to it as host `db` on port `5432`; Compose sets those two values itself, so `POSTGRES_HOST` and `POSTGRES_PORT` in `.env` do not affect the containers. Database name, user and password come from `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PASSWORD`.

```dotenv
DB_ENGINE=local
POSTGRES_DB=statement_ai_db
POSTGRES_USER=statement_ai_user
POSTGRES_PASSWORD=choose-a-password
```

Data is stored in the `postgres_data` Docker volume.

### Hosted Supabase database

Supabase is hosted PostgreSQL. The project connects to it with the same Django backend, so no code changes are needed. Create a project in the Supabase dashboard, then copy the connection values from **Project Settings → Database**. The pooler hosts usually suit container deployments better; the direct host also works for a single always-on container.

```dotenv
DB_ENGINE=supabase
SUPABASE_DB_HOST=your-host.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_SSLMODE=require
```

Use port `6543` with the transaction pooler. The migrations create the schema automatically; you do not create tables by hand. When `DEBUG=0`, host, user and password are required and the application refuses to start without them.

The `db` service has no Compose profile, and nothing in the repository stops it from starting when `DB_ENGINE=supabase`. An idle local PostgreSQL container is harmless, but it publishes port `5432` on the host.

## 4. Start the services

```bash
docker compose up -d --build
```

What happens:

1. The image is built from the `Dockerfile`.
2. `redis` and `db` start and wait for their health checks.
3. The one-off `migrate` service runs `python manage.py migrate --noinput`.
4. When migrations succeed, `web`, `worker` and `cron` start. If they fail, those three stay down.

Redis serves two purposes. Database `0` is the Celery broker (`CELERY_BROKER_URL`). Database `1` is the Django cache (`REDIS_URL`), which holds rate-limit and failed-login counters.

## 5. Optional admin user

```bash
docker compose exec web python manage.py createsuperuser
```

## 6. Verify the installation

```bash
docker compose ps
curl -i http://localhost:8001/api/statements/
```

`migrate` should be `Exited (0)`, the other services `running`, and the request should return `401 Unauthorized`. The Django admin is at `http://localhost:8001/admin/`.

For a fuller check, register a user, confirm the email and upload a statement as described in [Getting started]({{ '/getting-started/' | relative_url }}).

## Email in development and production

Registration confirmation and password reset both send email. With `DEBUG=1` and no `EMAIL_BACKEND` set, Django prints the messages to the web container log:

```bash
docker compose logs web | tail -n 40
```

The links in those messages point to `REGISTRATION_CONFIRMATION_URL` and `PASSWORD_RESET_URL`, with `uid` and `token` in the URL fragment. These are pages of your own client application. In development they default to `http://localhost:3000/...` and nothing has to listen there. With `DEBUG=0` you need working SMTP settings and absolute HTTPS URLs for both. Set `EMAIL_USE_HTML_TEMPLATES=1` to send an HTML version in addition to plain text; the templates are in `templates/emails/`.

## Scheduled cleanup

The `cron` service runs `python manage.py delete_expired_data` every day at 03:00 container time (UTC) and writes its output to the container log:

```bash
docker compose logs -f cron
```

Run it by hand at any time:

```bash
docker compose exec cron python manage.py delete_expired_data
```

To change the schedule, edit `cron/statement-ai-cron` and rebuild with `docker compose up -d --build cron`. If you do not want the container, remove the `cron` service and schedule `docker compose exec web python manage.py delete_expired_data` from the host. The command's exact effects are listed under [Security]({{ '/security/#retention-and-erasure' | relative_url }}).

## Running without Docker

The repository does not include a non-Docker guide, and the steps below are derived from `settings.py` rather than from a full run. You need Python 3.11, PostgreSQL and Redis (the worker needs a broker):

```bash
pip install -r requirements.txt
export DEBUG=1 SECRET_KEY=dev-only GEMINI_API_KEY=your-key
export POSTGRES_HOST=localhost
export CELERY_BROKER_URL=redis://localhost:6379/0
python manage.py migrate
python manage.py runserver 0.0.0.0:8001
celery -A statement_ai worker --loglevel=INFO
```

Run the last command in a second terminal. The default `POSTGRES_HOST` is `db`, the Compose service name, which is why it has to be overridden here.

## Runtime notes

- `web` runs `manage.py runserver 0.0.0.0:8001`, Django's development server.
- `worker` runs `celery -A statement_ai worker --loglevel=INFO --concurrency=2` as user `nobody`.
- The project directory is bind-mounted into the containers, so code changes show up without a rebuild. The worker does not reload by itself; run `docker compose restart worker` after changing task or service code.
- Uploaded PDFs are stored in the `media_data` volume, mounted at `/app/media`.

## Related pages

- [Getting started]({{ '/getting-started/' | relative_url }})
- [Configuration]({{ '/configuration/' | relative_url }})
- [Deployment]({{ '/deployment/' | relative_url }})
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }})
