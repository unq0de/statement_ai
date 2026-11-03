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
DATA_RETENTION_DAYS=365
DB_ENGINE=local
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=statement_ai_db
POSTGRES_USER=statement_ai_user
POSTGRES_PASSWORD=Test123!
ALLOWED_HOSTS=
CORS_ALLOWED_ORIGINS=
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

This starts the web and cron containers, as well as the PostgreSQL database service.

## 5. Apply migrations

```bash
docker compose exec web python manage.py migrate
```

If this is the first setup, the application can then be used immediately.

## 6. Optional admin user

```bash
docker compose exec web python manage.py createsuperuser
```

## 7. Access the application

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
