---
layout: page
title: Deployment
permalink: /deployment/
---

# Deployment

The repository ships a Docker Compose setup. It works well for local development; for production it needs some changes, which this page lists. Variable names are explained on the [Configuration]({{ '/configuration/' | relative_url }}) page.

## Compose services

| Service | Image and command | Purpose |
| --- | --- | --- |
| `web` | built from the `Dockerfile`, gunicorn serving `statement_ai.wsgi:application` on port `8001` | API and admin, published on host port `8001`. A health check polls `GET /health/` every 30 seconds. |
| `migrate` | same image, `python manage.py migrate --noinput` | One-off. `web`, `worker` and `cron` wait for it to complete successfully. |
| `worker` | same image, `celery -A statement_ai worker --loglevel=INFO --concurrency=2`, user `nobody` | Processes statements. |
| `cron` | same image, `sh /app/cron/entrypoint.sh` | Daily retention cleanup. |
| `redis` | `redis:7-alpine` with AOF persistence, a 256 MB limit and `noeviction` | Celery broker and cache. |
| `db` | `postgres:15-alpine`, port `5432` published | Local PostgreSQL with a health check. |

Volumes: `postgres_data` for the database, `media_data` for uploaded PDFs (mounted at `/app/media`), and `redis_data`.

The `cron` container writes its environment to `/etc/environment`, installs `cron/statement-ai-cron` into `/etc/cron.d/`, and runs cron in the foreground. The job calls `python manage.py delete_expired_data` at 03:00 container time (UTC) and sends the output to the container log. Change the schedule by editing `cron/statement-ai-cron` and running `docker compose up -d --build cron`.

## Local development versus production

| | Local development | Production |
| --- | --- | --- |
| `DEBUG` | `1` | `0` |
| Hosts and CORS | Everything allowed | `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` required |
| Email | Console backend | SMTP required, with TLS or SSL |
| Link URLs | Default to `localhost:3000` | Absolute HTTPS URLs required |
| Redis cache | Optional, in-process fallback | `REDIS_URL` required |
| `/media/` | Served by Django | Not served; use the download endpoint |
| Secrets | Placeholders are fine | Strong `SECRET_KEY`, stable `TWO_FACTOR_ENCRYPTION_KEY` |

With `DEBUG=0` the application refuses to start unless the required settings are present; the list is on the Configuration page under [Production checks]({{ '/configuration/#production-checks' | relative_url }}).

## Before exposing the stack to real users

All of these follow from the files in this repository:

- **Put a TLS-terminating reverse proxy in front.** `web` runs gunicorn, which is a production WSGI server but should not face the internet directly. Set `NUM_PROXIES` to match; otherwise rate limits see the proxy's IP address.
- **Do not publish PostgreSQL.** `docker-compose.yml` maps `5432:5432`. Remove that mapping or bind it to a private interface, and change `POSTGRES_PASSWORD`.
- **Think about the bind mount.** The source tree is mounted into the containers (`.:/app`). A production setup will probably prefer image-only containers.
- **Back up your data.** The `postgres_data` volume lives on the Docker host. Use a managed or backed-up database, and back up `media_data` as well. Make sure your web server does not expose the media directory.
- **Set the retention period on purpose.** `DATA_RETENTION_DAYS` decides how long statements survive.
- **Review the Gemini data transfer.** Every uploaded PDF goes to Google. See [Security]({{ '/security/#third-party-data-transfer' | relative_url }}).
- **Keep the worker running.** Without it, uploads stay `pending` forever.

## Hosted database

Setting `DB_ENGINE=supabase` makes the application connect to a hosted Supabase PostgreSQL database instead of the `db` container. The setup is described under [Installation]({{ '/installation/#choose-a-database' | relative_url }}). A managed database, from Supabase or from a cloud provider, is the better choice than the local container for anything beyond development, because its data does not depend on a Docker volume on one host.

## Scaling notes

- The web container starts three gunicorn workers. Raise `GUNICORN_WORKERS` or run more web containers for more concurrent API requests.
- The worker runs two processes. Raise `--concurrency` in `docker-compose.yml`, or run more worker containers, to process more statements in parallel. Each running job holds one Gemini request.
- `GEMINI_MONTHLY_LIMIT_PER_USER` and the upload limit of 5 per hour per user cap how much each account can send to Gemini.
- Rate-limit counters are shared across web processes only through Redis, so keep `REDIS_URL` pointed at a shared instance.

## Related pages

- [Installation]({{ '/installation/' | relative_url }})
- [Configuration]({{ '/configuration/' | relative_url }})
- [Security]({{ '/security/' | relative_url }})
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }})
