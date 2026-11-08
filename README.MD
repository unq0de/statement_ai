<div align="center">

# Statement AI

### A REST API that processes bank statements and categorizes transactions using Google Gemini

<p>
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/django-4.2-092E20?logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/DRF-3.14-red?logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/AI-Google%20Gemini-8E75B2?logo=googlegemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/queue-Celery%20%2B%20Redis-37814A?logo=celery&logoColor=white" alt="Celery and Redis" />
  <img src="https://img.shields.io/badge/database-PostgreSQL%2015-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/deploy-Docker-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

<p>
  <b>JWT Auth with optional 2FA</b> •
  <b>Background processing</b> •
  <b>AI categorization</b> •
  <b>Per-user isolation</b> •
  <b>GDPR compliant</b>
</p>

<p>
  <a href="#what-is-statement-ai">What is it?</a> •
  <a href="#quickstart">Quickstart</a> •
  <a href="#how-it-works">How it works</a> •
  <a href="#getting-started">Getting started</a> •
  <a href="#first-steps">First steps</a> •
  <a href="#api-endpoints">API</a> •
  <a href="#security">Security</a> •
  <a href="docs/api-reference/">Full API Docs</a>
</p>

</div>

---

## What is Statement AI?

You upload a PDF bank statement. Statement AI sends it to Google Gemini, which extracts and categorizes each transaction. The structured data is stored in a database where you can query it via a REST API.

That's it. No local PDF parsing, no transaction editing, no complex setup.

### What you can build with this

- Personal finance dashboards
- Automated budget tracking apps
- Expense categorization systems
- Financial data pipelines
- Integration layers for fintech apps

### The API does

- User registration and email-based account confirmation
- PDF uploads (up to 10 MB) with immediate acknowledgment
- Background processing via Celery workers
- AI categorization of transactions
- Per-user data isolation and storage
- Data export as JSON, PDF download, full account deletion
- GDPR-compliant automatic data retention
- Optional TOTP two-factor authentication
- Rate limiting on auth and upload endpoints

### The API doesn't do

- Parse PDFs locally (they go straight to Gemini)
- Support transaction editing (delete and re-upload instead)
- Compute analytics (only stores AI summaries)

---

## Quickstart

You need Docker Compose and a [Google Gemini API key](https://aistudio.google.com/apikey).

### 1. Clone and prepare

```bash
git clone https://github.com/unq0de/statement_ai.git
cd statement_ai
cp .env.example .env
```

### 2. Configure environment

Edit `.env`:
- `SECRET_KEY`: Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- `GEMINI_API_KEY`: Your Gemini API key
- `DEBUG=1` for local work

**Important**: `DATA_RETENTION_DAYS=1` in the example means statements older than 1 day get auto-deleted. Change this to `365` or higher for production unless you want daily purges.

### 3. Start everything

```bash
docker compose up -d --build
```

This starts the web API, Celery worker, PostgreSQL, Redis, and a cron container for cleanup.

### 4. Verify it's running

```bash
curl -i http://localhost:8001/api/statements/
```

You should get `401 Unauthorized` – that's good, it means auth is enforced.

### 5. Create an admin user (optional)

```bash
docker compose exec web python manage.py createsuperuser
```

Now head to [First steps](#first-steps) to create a test account and upload a PDF.

---

## How it works

### The flow

1. User uploads a PDF statement
2. API validates and stores it immediately, returns 202 Accepted
3. Celery worker picks up the job and sends the PDF to Gemini
4. Gemini extracts transactions: date, amount, category, payee, description
5. Results are stored in PostgreSQL
6. User queries the API for transactions and summaries

### User perspective

- Register → confirm email → log in → get JWT token
- Upload PDF → get immediate confirmation
- Check status → wait until `processing_status=completed`
- Read transactions via `/transactions/` or `/statements/{id}/transactions/`
- Download original PDF or export everything as JSON
- Delete statements or entire account anytime

### Data flow

```
PDF Upload → API validation → Redis queue → Celery worker
                                                  ↓
                                            Google Gemini
                                                  ↓
                                          Parse response
                                                  ↓
                                          Store in PostgreSQL
                                                  ↓
                                    User queries via API
```

---

## Key features

### Authentication

Registration sends a confirmation email. After confirming, users log in with username/email and password. Login returns an access token (60 min) and refresh token (1 day). Tokens are invalidated by password changes or when 2FA is toggled.

Optional TOTP 2FA with any authenticator app. Users get one-time recovery codes shown once.

Password policy enforced: 12+ characters minimum, at least one special character, not similar to username.

### Upload and processing

Uploads are validated for PDF format and size (10 MB max), stored immediately, and processed asynchronously. Clients can poll the status endpoint. Failed jobs retry up to 3 times with exponential backoff.

Optional per-user monthly caps limit Gemini usage.

### Transactions

Each extracted transaction has date, signed amount (negative = out, positive = in), payee/payer, description, transaction type, and category (one of 15 predefined categories).

Each statement gets an AI summary: up to 3 sentences in English, regardless of the PDF language.

Transactions are queryable as a flat list or nested within statements. Filters and search are supported.

### Data and privacy

Users can download their original PDFs, export their full profile and transaction history as JSON, delete individual statements, delete all statements, or delete their entire account.

A scheduled job purges statements older than `DATA_RETENTION_DAYS` and cleans up associated usage records and audit logs.

### Rate limiting and abuse protection

IP-based and user-based rate limits on registration, login, password reset, 2FA, and uploads. Failed login attempts trigger per-IP cooldowns.

Operators get read-only admin views for API usage, Gemini usage, and audit logs.

---

## Architecture

### Components

| Part | Purpose |
|------|---------|
| **web** (Django + DRF) | REST API, request validation, JWT auth, file storage, job queuing |
| **worker** (Celery) | PDF processing, Gemini calls, result persistence |
| **Redis** | Message broker for Celery and cache backend for rate limits |
| **PostgreSQL** | Users, statements, transactions, audit logs, usage records |
| **cron** | Daily cleanup of expired data (runs at 03:00 UTC) |
| **media volume** | PDF storage (`statements/YYYY/MM/`) shared across all services |
| **Google Gemini** | AI parsing and categorization (model: `gemini-3.5-flash-lite` by default) |

### Request pipeline

```
User → API endpoint → Authentication check
  ↓
Request validation
  ↓
Business logic (file storage, queuing, DB writes)
  ↓
Response back to user
```

For PDF processing specifically:

```
Upload endpoint → File validation & storage → Enqueue Celery task → Return 202
  ↓
Celery worker (background) → Call Gemini → Parse response → Save to DB
```

---

## Getting started

### Prerequisites

- Docker and Docker Compose
- Google Gemini API key (free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey))

### Local development without Docker

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

You'll still need Redis and PostgreSQL (or SQLite for testing).

### Docker Compose services

- **web**: Django API on port 8001
- **worker**: Celery worker (default 2 processes)
- **db**: PostgreSQL 15
- **redis**: Message broker and cache
- **cron**: Cleanup container (runs daily at 03:00 UTC)
- **migrate**: One-off migrations container

Check logs with `docker compose logs -f <service>`.

---

## First steps

### 1. Create a user

```bash
curl -X POST http://localhost:8001/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'
```

In local development, confirmation emails print to the console. Alternatively, activate manually:

```bash
docker compose exec web python manage.py shell << 'PYEOF'
from django.contrib.auth.models import User
u = User.objects.get(username="testuser")
u.is_active = True
u.save()
print("Account activated")
PYEOF
```

### 2. Log in

```bash
RESPONSE=$(curl -s -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePass123!"
  }')

TOKEN=$(echo $RESPONSE | jq -r '.access')
```

### 3. Upload a PDF

Use any real PDF or create a test one. Then:

```bash
curl -X POST http://localhost:8001/api/statements/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/statement.pdf"
```

Note the returned `id`.

### 4. Check processing status

```bash
curl http://localhost:8001/api/statements/{id}/status/ \
  -H "Authorization: Bearer $TOKEN"
```

Wait until `processing_status` is `completed`.

### 5. Read the transactions

```bash
curl http://localhost:8001/api/transactions/ \
  -H "Authorization: Bearer $TOKEN"
```

Done.

---

## API endpoints

Here's a quick overview. For complete documentation with curl examples, data schemas, error codes and workflows, see:
- **[Complete API Documentation](docs/API.md)** (2400+ lines with every detail)
- **[API Reference by Category](docs/api-reference/)** (organized guide)

### Auth

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/register/` | POST | Create account |
| `/auth/register/confirm/` | POST | Confirm email |
| `/auth/login/` | POST | Get tokens |
| `/auth/refresh/` | POST | Refresh access token |
| `/auth/password-reset/` | POST | Request reset |
| `/auth/password-reset/confirm/` | POST | Set new password |
| `/auth/2fa/setup/` | POST | Initialize 2FA |
| `/auth/2fa/enable/` | POST | Activate 2FA |
| `/auth/2fa/disable/` | POST | Disable 2FA |
| `/auth/account/` | DELETE | Delete account |
| `/auth/export/` | GET | Export all data as JSON |

**Details**: See [Authentication endpoints](docs/api-reference/authentication.md).

### Statements

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/statements/upload/` | POST | Upload PDF |
| `/statements/` | GET | List statements |
| `/statements/{id}/` | GET | View statement details |
| `/statements/{id}/status/` | GET | Check processing status |
| `/statements/{id}/file/` | GET | Download original PDF |
| `/statements/{id}/` | DELETE | Delete statement |
| `/statements/analytics/` | GET | Get AI summaries |

**Details**: See [Statement endpoints](docs/api-reference/statements.md).

### Transactions

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/transactions/` | GET | List all transactions |
| `/transactions/{id}/` | GET | View transaction |

**Details**: See [Transaction endpoints](docs/api-reference/transactions.md).

---

## Security

### What's protected

- All endpoints except `/health/` require JWT authentication
- Passwords are hashed (never stored in plain text)
- PDFs are not analyzed locally; they're sent to Google Gemini
- Rate limiting prevents brute force attacks
- 2FA adds an optional second factor
- All user data is strictly isolated (you can't see other users' data)

### What Google Gemini sees

Your PDF file is uploaded to Google's servers for AI processing. This is necessary for categorization. After processing, your PDF is not retained by Google (but see their privacy policy for details).

### GDPR compliance

- Users can export all their data as JSON
- Users can delete their entire account and all associated data
- Automatic cleanup purges old statements based on `DATA_RETENTION_DAYS`
- All data is per-user; no cross-user leakage

---

## Configuration

### Core settings

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | Required | Django secret key |
| `DEBUG` | False | Enable debug mode |
| `ALLOWED_HOSTS` | `*` | Allowed hostnames |
| `GEMINI_API_KEY` | Required | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | AI model to use |

### Database

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///db.sqlite3` | Database connection string |

Use PostgreSQL for production: `postgresql://user:pass@host/dbname`

Alternatively, use [Supabase](https://supabase.com) (free tier available).

### Redis and Celery

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery message broker |

### Authentication

| Variable | Default | Purpose |
|----------|---------|---------|
| `PASSWORD_MIN_LENGTH` | 12 | Minimum password length |
| `TWO_FACTOR_ENABLED` | 1 | Enable 2FA endpoints |

### Data retention

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATA_RETENTION_DAYS` | 365 | Days before statement auto-delete |
| `API_USAGE_RETENTION_DAYS` | 90 | Days to keep API logs |
| `GEMINI_USAGE_RETENTION_DAYS` | 90 | Days to keep Gemini call logs |

### Rate limiting

| Variable | Default | Purpose |
|----------|---------|---------|
| `RATE_LIMIT_AUTH` | 5/hour | Login attempts per IP |
| `RATE_LIMIT_UPLOAD` | 20/day | Uploads per user |

---

## Deployment

### Docker

```bash
docker build -t statement-ai .
docker run -d \
  -p 8000:8000 \
  -e SECRET_KEY=... \
  -e GEMINI_API_KEY=... \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  statement-ai
```

### Google Cloud Run

```bash
gcloud run deploy statement-ai \
  --source . \
  --region europe-west1 \
  --memory 512Mi \
  --set-env-vars SECRET_KEY=...,GEMINI_API_KEY=...
```

### Using Supabase instead of local PostgreSQL

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Copy the connection string
3. Set `DATABASE_URL` in your `.env`

Redis can stay local or use a managed service like Upstash.

---

## Development

### Run tests

```bash
docker compose exec web python manage.py test
```

### Useful commands

```bash
# Database migrations
docker compose exec web python manage.py migrate

# Create admin user
docker compose exec web python manage.py createsuperuser

# Access Django shell
docker compose exec web python manage.py shell

# View logs
docker compose logs -f web      # API logs
docker compose logs -f worker   # Celery logs
docker compose logs -f db       # Database logs

# Stop everything
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

### Linting and formatting

```bash
# Black (formatter)
black statements/ statement_ai/

# Flake8 (linter)
flake8 statements/ statement_ai/

# isort (import sorting)
isort statements/ statement_ai/
```

---

## Common questions

**Q: Can I edit transactions?**  
A: No. Delete and re-upload the statement instead.

**Q: What are transaction categories?**  
A: Housing & Utilities, Groceries & Food, Dining Out, Transportation, Shopping, Subscriptions, Health, Financial, Salary, Secondary Income, Transfers, Education, Travel, Cash, Miscellaneous.

**Q: Does this cost money?**  
A: The API is free (MIT licensed). Gemini API calls cost based on usage; check Google's pricing.

**Q: How long are statements kept?**  
A: By default, 365 days. Configurable via `DATA_RETENTION_DAYS`.

**Q: Is this GDPR compliant?**  
A: Yes. Users can export and delete their data, and automatic cleanup respects retention policies.

**Q: Can I self-host?**  
A: Yes. It's open source. Use Docker or deploy to your own servers.

**Q: How do I add another AI provider instead of Gemini?**  
A: Look at `statements/services.py` – specifically the `process_pdf_statement_with_gemini()` function. It calls the Gemini API and parses the response. You can swap in another provider (Claude, OpenAI, etc.) by changing that function.

---

## Project structure

```
statement_ai/
├── statements/                 # Main app
│   ├── models.py              # BankStatement, Transaction, etc.
│   ├── views.py               # API endpoints
│   ├── serializers.py         # DRF serializers
│   ├── services.py            # Business logic (Gemini integration)
│   ├── tasks.py               # Celery tasks
│   └── tests.py               # Unit and integration tests
├── statement_ai/
│   ├── settings.py            # Django configuration
│   ├── urls.py                # URL routing
│   └── wsgi.py                # WSGI entry point
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Local development stack
├── requirements.txt           # Python dependencies
├── manage.py                  # Django CLI
└── cron                       # Cron job script
```

---

## Troubleshooting

### 401 Unauthorized on every request

Check that you're sending the `Authorization: Bearer <token>` header. Make sure the token hasn't expired (60 min lifespan). Use `/auth/refresh/` to get a new one.

### PDF processing fails

Check Celery worker logs: `docker compose logs -f worker`

Common issues:
- Gemini API key not set or invalid
- PDF is corrupted
- PDF is too large (>10 MB)

### Database migration errors

```bash
docker compose exec web python manage.py migrate --noinput
```

If that fails, check that PostgreSQL is running and the `DATABASE_URL` is correct.

### Rate limited

You're making too many requests in a short time. Wait a few minutes and retry.

---

## Documentation

For more details, see the `docs/` directory or our online docs at [unq0de.github.io/statement_ai/](https://unq0de.github.io/statement_ai/).

---

## License

MIT. See [LICENSE](LICENSE).

---

**Questions?** Open an issue on [GitHub](https://github.com/unq0de/statement_ai/issues).
