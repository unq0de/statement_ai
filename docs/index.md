---
layout: home
title: Statement AI
---

<div align="center">

# Statement AI

A REST API that reads bank statement PDFs with Google Gemini, stores every transaction with a category, and writes a short summary of each statement.

<p>
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/django-4.2-092E20?logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/drf-3.14-red?logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/queue-celery%20%2B%20redis-37814A?logo=celery&logoColor=white" alt="Celery and Redis" />
  <img src="https://img.shields.io/badge/postgres-15-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/gemini-ai-8E75B2?logo=googlegemini&logoColor=white" alt="Google Gemini" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
</p>

[Getting started]({{ '/getting-started/' | relative_url }}) ·
[Installation]({{ '/installation/' | relative_url }}) ·
[Configuration]({{ '/configuration/' | relative_url }}) ·
[Features]({{ '/features/' | relative_url }}) ·
[Architecture]({{ '/architecture/' | relative_url }}) ·
[API Reference]({{ '/api-reference/' | relative_url }}) ·
[Security]({{ '/security/' | relative_url }}) ·
[Development]({{ '/development/' | relative_url }}) ·
[Deployment]({{ '/deployment/' | relative_url }}) ·
[Troubleshooting]({{ '/troubleshooting/' | relative_url }})

</div>

## What this project does

A bank statement is usually a PDF, and a PDF is hard to work with. Statement AI takes the PDF, sends it to Google Gemini, and saves what comes back as structured data: one record per transaction with a date, an amount, a counterparty, a transaction type and a spending category, plus a short evaluation of the statement as a whole.

Everything is served through a JWT-secured REST API. There is no web interface. The project is meant for developers who want to build a budgeting app, a personal-finance dashboard or a data pipeline on top of statement data without writing their own PDF extraction.

The flow looks like this:

1. Register, confirm the email address and log in.
2. Upload a PDF statement. The API checks it and answers right away with `202 Accepted`.
3. A background worker sends the PDF to Gemini and stores the result.
4. Poll the status endpoint until the statement is `completed`.
5. Read the transactions and the AI evaluation, or export and delete your data.

## What it can do

- Email-confirmed registration, JWT login, token refresh and password reset by email
- Optional TOTP two-factor authentication with one-time recovery codes
- PDF upload with type, content and size checks (10 MB maximum)
- Background processing with Celery and Redis, automatic retries and a visible processing status
- Transaction extraction and categorization with Google Gemini
- A short AI-written evaluation for every processed statement
- Filtering, searching and sorting of transactions
- Original PDF download, JSON data export, and deletion of single statements, all statements or the whole account
- Rate limiting, failed-login cooldown, and per-user data isolation
- API usage records, Gemini usage records and an audit log, all read-only in Django admin
- A scheduled cleanup job that applies the configured retention periods
- Docker Compose setup with PostgreSQL, or a hosted Supabase database

## What it does not do

- It does not parse PDFs locally. The whole file goes to Gemini.
- It does not let you create, edit or delete individual transactions.
- It does not calculate totals or other numeric statistics. The analytics endpoint returns the AI-written summaries only.
- It does not detect duplicates. Uploading the same PDF twice creates two statements.

The [Features]({{ '/features/' | relative_url }}) page explains each area in detail.

## Quick start

You need Docker with Docker Compose and a [Gemini API key](https://aistudio.google.com/apikey).

```bash
git clone https://github.com/unq0de/statement_ai.git
cd statement_ai
cp .env.example .env
```

Set `SECRET_KEY` and `GEMINI_API_KEY` in `.env`. Also change `DATA_RETENTION_DAYS`: the example file sets it to `1`, which makes the daily cleanup job delete every statement older than a day.

```bash
docker compose up -d --build
```

The one-off `migrate` service applies the database schema before the API, worker and cron services start. The API is then available at:

```text
http://localhost:8001/api/
```

The [Getting started]({{ '/getting-started/' | relative_url }}) guide continues from here and walks through registration, login and a first upload.

## Project structure

```text
statement_ai/
├── statement_ai/         # Django project: settings, URL config, Celery app
├── statements/           # The application: models, views, serializers, tasks, tests
├── templates/emails/     # Confirmation and password-reset email templates
├── cron/                 # Entrypoint and crontab for the retention cleanup
├── tools/                # Script that generates synthetic test PDFs
├── docs/                 # This documentation (GitHub Pages)
├── Dockerfile            # Application image
├── docker-compose.yml    # web, migrate, worker, cron, redis and db services
├── manage.py             # Django entry point
├── requirements.txt      # Python requirements
├── .env.example          # Environment template
└── README.MD             # Project overview
```

[Development]({{ '/development/' | relative_url }}) has a more detailed tour of the code.

## Where to go next

- [Getting started]({{ '/getting-started/' | relative_url }}) for a first run
- [Installation]({{ '/installation/' | relative_url }}) for Docker and database setup
- [Configuration]({{ '/configuration/' | relative_url }}) for every environment variable
- [Features]({{ '/features/' | relative_url }}) for what each part does
- [Architecture]({{ '/architecture/' | relative_url }}) for components, data model and workflows
- [API reference]({{ '/api-reference/' | relative_url }}) for every endpoint
- [Security]({{ '/security/' | relative_url }}) for privacy, access control and retention
- [Development]({{ '/development/' | relative_url }}) for tests, commands and CI
- [Deployment]({{ '/deployment/' | relative_url }}) for production considerations
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }}) for common problems

## Repository

- [GitHub repository](https://github.com/unq0de/statement_ai)
- [README](https://github.com/unq0de/statement_ai#readme)
