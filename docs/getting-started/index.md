---
layout: page
title: Getting Started
permalink: /getting-started/
---

# Getting started

This guide takes you from a fresh clone to your first processed bank statement. It uses Docker Compose, which is the supported way to run the project.

The steps are:

1. Clone the repository and create an environment file.
2. Start the stack with Docker Compose.
3. Check that the API is up.
4. Register a user and confirm the email address.
5. Log in, upload a PDF and read the result.

## Prerequisites

- Docker and Docker Compose
- A Google Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- A terminal with Git and `curl`
- A PDF bank statement. If you would rather not use a real one, see [Test PDFs](#test-pdfs) below.

## Step 1: Clone the repository and configure it

```bash
git clone https://github.com/unq0de/statement_ai.git
cd statement_ai
cp .env.example .env
```

Open `.env` and set:

- `SECRET_KEY`: any long random string
- `GEMINI_API_KEY`: your Gemini key
- `DATA_RETENTION_DAYS`: change it from `1` to something like `365`. The cleanup job runs every night and deletes statements older than this many days, so with `1` your uploads would disappear the next day.

Keep `DEBUG=1` for local work. In this mode emails are printed to the log instead of being sent, and no SMTP server is needed. The other variables are described on the [Configuration]({{ '/configuration/' | relative_url }}) page.

## Step 2: Start the stack

```bash
docker compose up -d --build
```

This starts:

- `web`: the Django API on port `8001`
- `worker`: the Celery worker that processes statements
- `redis`: the Celery broker and the cache used for rate limits
- `db`: a local PostgreSQL database
- `cron`: the nightly retention cleanup
- `migrate`: a one-off service that applies database migrations first

If a migration fails, `web`, `worker` and `cron` do not start. Use `sudo` in front of `docker` if your setup needs it.

## Step 3: Check that the API is up

```bash
docker compose ps
curl -i http://localhost:8001/api/statements/
```

`migrate` should show as exited with code 0 and the other services as running. The `curl` call should return `401 Unauthorized`. That confirms the API is running and enforcing authentication. There is no API root page or health endpoint, so opening `/api/` in a browser gives a 404.

## Step 4: Optional admin account

```bash
docker compose exec web python manage.py createsuperuser
```

The admin is at `http://localhost:8001/admin/`. It shows API usage, Gemini usage and the audit log.

## Step 5: Register and confirm your email

```bash
curl -X POST http://localhost:8001/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"StrongPass123!"}'
```

The account is created inactive and cannot log in yet. Passwords must be at least 12 characters, must not be too common or too similar to the username or email, must not be all digits, and must contain at least one punctuation mark or symbol.

Because `DEBUG=1`, the confirmation email appears in the web logs:

```bash
docker compose logs web | tail -n 40
```

The link looks like `http://localhost:3000/confirm-email/#uid=MQ&token=...`. Nothing needs to listen on port 3000. Copy the `uid` and `token` values from the part after `#` and send them to the confirm endpoint:

```bash
curl -X POST http://localhost:8001/api/auth/register/confirm/ \
  -H "Content-Type: application/json" \
  -d '{"uid":"MQ","token":"<token_from_the_link>"}'
```

The link is valid for one hour by default.

## Step 6: Log in

```bash
curl -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"StrongPass123!"}'
```

The response contains an `access` token, valid for 60 minutes, and a `refresh` token, valid for one day. Send the access token on every later request as `Authorization: Bearer <access_token>`.

## Step 7: Upload a statement

```bash
curl -X POST http://localhost:8001/api/statements/upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/statement.pdf"
```

The API checks that the file is a PDF no larger than 10 MB, stores it, and answers immediately:

```json
{
  "message": "Bank statement accepted for processing.",
  "statement_id": 1,
  "processing_status": "pending",
  "status_url": "/api/statements/1/status/"
}
```

At this point nothing has been extracted yet. The worker picks the job up in the background.

## Step 8: Wait for processing and read the result

Poll the status URL until `processing_status` is `completed` or `failed`:

```bash
curl http://localhost:8001/api/statements/1/status/ \
  -H "Authorization: Bearer <access_token>"
```

The duration depends on the document and on Gemini. Once the status is `completed`, read the transactions:

```bash
curl http://localhost:8001/api/transactions/ \
  -H "Authorization: Bearer <access_token>"
```

The statement itself, with its transactions and the AI evaluation, is at `/api/statements/1/`. If the status becomes `failed`, check `docker compose logs worker`; the [Troubleshooting]({{ '/troubleshooting/' | relative_url }}) page lists the usual causes.

## Test PDFs

`tools/generate_test_statement_pdfs.py` writes synthetic statement PDFs into a git-ignored `testdata/` directory, so you can try the upload without real financial data:

```bash
python tools/generate_test_statement_pdfs.py
```

## Next steps

- [Workflows]({{ '/architecture/#core-workflows' | relative_url }}) explain what happens at each stage.
- [Installation]({{ '/installation/' | relative_url }}) covers the services and the Supabase option.
- [Configuration]({{ '/configuration/' | relative_url }}) lists every setting.
- The [API reference]({{ '/api-reference/' | relative_url }}) documents every endpoint.
