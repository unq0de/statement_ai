---
title: Getting Started
layout: default
---

# Getting Started

## Prerequisites

- Docker & Docker Compose
- A [Google Gemini API key](https://aistudio.google.com/apikey)

## Installation

**1. Clone and configure**

```bash
git clone https://github.com/<your-username>/statement-ai.git
cd statement-ai
```

```bash
cp .env.example .env
```

Then fill in your own values in `.env`.

**2. Build and start the containers**

```bash
sudo docker compose up -d --build
```

**3. Run database migrations**

```bash
sudo docker compose exec web python manage.py migrate
```

The API is then available at `http://localhost:8000/api/`.

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | `1` for development, `0` for production | `0` |
| `GEMINI_API_KEY` | Your Google Gemini API key | `AI...` |
| `DB_ENGINE` | `local` (default, docker Postgres) or `supabase` | `supabase` |
| `POSTGRES_DB` | Database name (only used if `DB_ENGINE=local`) | `statement_ai_db` |
| `POSTGRES_USER` | Database user (only used if `DB_ENGINE=local`) | `statement_ai_user` |
| `POSTGRES_PASSWORD` | Database password (only used if `DB_ENGINE=local`) | `********` |
| `SUPABASE_DB_HOST` | Supabase Postgres host (only used if `DB_ENGINE=supabase`) — direct or pooler host, see [Using Supabase]({{ site.baseurl }}/supabase/) | `db.xxxxxxxxxxxx.supabase.co` |
| `SUPABASE_DB_PORT` | Supabase Postgres port (only used if `DB_ENGINE=supabase`) — `5432` direct, `6543` if using the pooler | `5432` |
| `SUPABASE_DB_NAME` | Supabase database name (only used if `DB_ENGINE=supabase`) | `postgres` |
| `SUPABASE_DB_USER` | Supabase database user (only used if `DB_ENGINE=supabase`) | `postgres` |
| `SUPABASE_DB_PASSWORD` | Supabase database password (only used if `DB_ENGINE=supabase`) | `********` |
| `SUPABASE_DB_SSLMODE` | SSL mode for the Supabase connection (only used if `DB_ENGINE=supabase`); Supabase requires TLS | `require` |
| `ALLOWED_HOSTS` | Comma-separated hosts (production only) | `api.example.com` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins (production only) | `https://app.example.com` |
| `DATA_RETENTION_DAYS` | Days a bank statement is kept before it becomes eligible for automatic deletion | `365` |

> ⚠️ **Warning:** Never commit your `.env` file. Rotate `SECRET_KEY` and `GEMINI_API_KEY` immediately if they are ever exposed.

## Scheduled Data Retention Cleanup

Bank statements older than `DATA_RETENTION_DAYS` are cleaned up automatically by a dedicated `cron` service in `docker-compose.yml`. It runs the same image as `web`, but only executes `manage.py delete_expired_data` on a daily schedule (`cron/statement-ai-cron`, default `03:00`) and otherwise stays idle.

It starts automatically with:

```bash
sudo docker compose up -d --build
```

Check that it's running and inspect its logs with:

```bash
sudo docker compose logs -f cron
```

You can also trigger a cleanup manually at any time — both the `web` and `cron` services share the same code and database:

```bash
sudo docker compose exec cron python manage.py delete_expired_data
```

This permanently deletes every bank statement (and its transactions and PDF file) whose `uploaded_at` is older than the configured retention period. To change the schedule, edit `cron/statement-ai-cron` and rebuild the `cron` service.

> ℹ️ **Note:** If you'd rather not run the sidecar container, remove the `cron` service from `docker-compose.yml` and schedule `docker compose exec web python manage.py delete_expired_data` via the host's system cron instead.
