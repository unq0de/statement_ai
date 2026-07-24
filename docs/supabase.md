---
title: Using Supabase
layout: default
---

# Using Supabase Instead of the Local Postgres Container

Supabase is a hosted **PostgreSQL** database. This project already talks to Postgres via Django's `psycopg2` backend, so pointing it at Supabase is just a matter of changing connection settings:

- No code changes
- No different driver
- No REST API involved

## 1. Create the Supabase Project *(manual, one-time)*

1. Go to [supabase.com](https://supabase.com) → **New project** → pick a name, region, and a database password.
2. Go to **Project Settings → Database → Connection parameters** and note the `Host`, `Port`, `Database name` (`postgres` by default), `User`, and your password.
   - Use the **Session pooler** or **Transaction pooler** host for most deployments — it works better with container restarts and multiple workers.
   - The **direct connection** host also works for a single always-on container like this one.

> ℹ️ **Note:** The Supabase **project** must be created manually in the dashboard — there's no "create project" API call to run from app code. Everything *inside* it (tables, columns, indexes) is created automatically in step 3.

## 2. Configure Environment Variables

Add the following to your `.env`:

```bash
DB_ENGINE=supabase
SUPABASE_DB_HOST=db.xxxxxxxxxxxx.supabase.co   # or the pooler host
SUPABASE_DB_PORT=5432                          # 6543 if using the pooler
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-db-password
SUPABASE_DB_SSLMODE=require
```

## 3. Create the Schema

You do **not** need to create tables manually in the Supabase SQL editor. The existing Django migrations create the exact same schema automatically — `BankStatement`, `Transaction`, plus Django's own `auth_user`, `django_session`, and so on.

**Start the stack**

```bash
docker compose up -d --build
```

With `DB_ENGINE=supabase` set in `.env`, the local `db` service is skipped automatically — it only starts for `DB_ENGINE=local`, so there's no need to name `web`/`cron` explicitly anymore.

**Run migrations**

```bash
docker compose exec web python manage.py migrate
```

**Create an admin user** *(optional, for `/admin`)*

```bash
docker compose exec web python manage.py createsuperuser
```

That's it — zero changes needed to `models.py`, `views.py`, or `serializers.py`.

## How Access Works *(no REST API needed for the database)*

- Django connects to Supabase's Postgres **directly over the Postgres wire protocol** via `psycopg2` (already in `requirements.txt`) — the same way it talks to the local container today. This is the correct way to use Supabase from a Django backend.
- Supabase's REST/GraphQL API (PostgREST) and the `supabase-py` SDK are a *different, optional* layer meant for client-side apps without their own backend. Since Django already **is** the backend and owns the schema via migrations, neither is needed for database access.
- `supabase-py` only becomes relevant if you later want other Supabase services from this backend — for example, Supabase Storage for the PDF files.

## Is Supabase Worth It Here, or Better to Self-Host on GCP/AWS?

Both connect the same way (plain Postgres), so this is an ops/hosting tradeoff, not a code one:

| | **Supabase** | **Self-Hosted Postgres (Cloud SQL / RDS)** |
|---|---|---|
| Setup effort | Minutes, via dashboard | You provision and manage the instance yourself |
| Ops burden | Backups, patching, scaling handled for you | You own backups, patching, HA, monitoring |
| Cost at small scale | Generous free tier | Smallest Cloud SQL/RDS tiers often cost more for the same workload |
| Data residency | Limited region choice, EU regions available | Full control — matters for strict GDPR residency needs |
| Vendor lock-in | Low — vanilla Postgres, portable via `pg_dump`/`pg_restore` | None, but you own the ops |
| Extra features | Auth, Storage, Realtime available if needed later | None built-in |

This project already has its own GDPR/retention logic (`delete_expired_data`), JWT auth, and per-user isolation, and doesn't need Supabase's Auth/Storage/Realtime:

- **Supabase** is the better fit if you want a managed Postgres fast with minimal ops, and might use Supabase Storage for PDFs later.
- **Cloud SQL / RDS** is the better fit if the API itself will run in GCP/AWS anyway (Cloud Run, ECS, etc.) — one cloud account, one network boundary, one bill, tighter region/VPC control.
- Either is **strictly better than the local Docker Postgres** for anything beyond local dev, since that container's data lives only in an unmanaged Docker volume.

> 💡 **Suggestion:** If you're not already committed to GCP/AWS for the rest of the stack, start with Supabase for the fastest path to a properly managed, backed-up Postgres. Since it's plain Postgres underneath, migrating later to Cloud SQL/RDS is a standard `pg_dump`/`pg_restore` — no Django code changes required.

> ✅ **Tip:** All variables in the table above — including `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and the `POSTGRES_*` credentials — are forwarded from `.env` into the `web`, `cron`, and `db` containers via `docker-compose.yml`. Changing a value in `.env` and rebuilding is enough; you don't need to edit `docker-compose.yml` by hand.
