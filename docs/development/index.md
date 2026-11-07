---
layout: page
title: Development
permalink: /development/
---

# Development

This page is for people who want to work on the code: the development environment, useful commands, tests, CI and a tour of the repository.

## Environment

Develop with the same Docker Compose stack as in [Getting started]({{ '/getting-started/' | relative_url }}), with `DEBUG=1`. The project directory is bind-mounted into the `web`, `migrate`, `worker` and `cron` containers, and `web` runs Django's `runserver`, so code changes take effect without a rebuild. The Celery worker does not reload by itself. After changing task or service code, restart it:

```bash
docker compose restart worker
```

## Useful commands

```bash
# logs
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f cron

# Django shell and migrations
docker compose exec web python manage.py shell
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# run the retention cleanup now
docker compose exec cron python manage.py delete_expired_data
```

After adding a migration, either run `migrate` as shown, or bring the stack up again with `docker compose up -d`; the `migrate` service applies pending migrations on start.

## Tests

All tests are in `statements/tests.py`, in one `TestCase` class, `StatementApiTests`. They use Django's test runner and DRF's `APIClient`. Gemini and Celery are mocked, so the tests need neither an API key nor a broker. The settings use PostgreSQL, so run the tests inside the Compose stack:

```bash
docker compose exec web python manage.py test
```

The test command is derived from the project layout; it has not been executed as part of writing this documentation.

The tests cover:

- registration, email confirmation, resend and password policy
- password reset and token revocation
- two-factor setup, login, recovery codes, lockout and global disabling
- rate limits and the failed-login cooldown
- API usage tracking and the audit log
- upload validation and queueing, the monthly limit, and Gemini usage records
- the processing task
- data isolation between users, bulk deletion, and transaction filtering and sorting

## Test PDFs

`tools/generate_test_statement_pdfs.py` writes synthetic statement PDFs to a git-ignored `testdata/` directory, so you can test uploads without real financial documents:

```bash
python tools/generate_test_statement_pdfs.py
```

## Linting, formatting and builds

The repository has no linter or formatter configuration and no build step beyond `docker compose build`. `.gitignore` mentions Ruff and mypy caches, but no Ruff or mypy configuration is checked in.

## Continuous integration

| Workflow | Trigger | What it does |
| --- | --- | --- |
| `codacy.yml` | Push and pull request to `main`, plus a weekly schedule | Codacy security scan, uploaded as SARIF. |
| `pages.yml` | Push to `main`, or manually | Builds `docs/` with Jekyll and deploys it to GitHub Pages. |

No workflow runs the tests.

## Debugging

Logs go to stdout. Failed Gemini calls and processing exceptions are logged with tracebacks by `worker`. For a statement stuck in `failed`, read `docker compose logs worker` and open the Gemini usage records in the admin, where `error_type` holds the exception class. With `DEBUG=1`, outgoing emails are printed in the `web` log.

## Code tour

```text
statement_ai/                    Django project
├── settings.py                  All configuration, env parsing, production checks, rate limits
├── urls.py                      /admin/ and /api/ (media only when DEBUG)
├── celery.py                    Celery app, reads the CELERY_* settings
└── wsgi.py
statements/                      The application
├── models.py                    Statements, transactions, usage, audit and 2FA models
├── views.py                     All API views
├── urls.py                      Route table for /api/
├── serializers.py               Serializers, login and refresh logic
├── services.py                  Gemini prompt, call and result storage
├── tasks.py                     Celery task: status handling and retries
├── two_factor.py                TOTP, recovery codes, challenges, token issuing
├── authentication.py            JWT authentication with the auth_version check
├── middleware.py                Usage tracking and rate limiting
├── throttles.py                 Failed-login cooldown
├── exceptions.py                Project-wide DRF exception handler
├── password_validators.py       Special-character validator
├── audit.py, usage.py           Audit event helper, monthly window helper
├── email_utils.py               Text and HTML email sending
├── admin.py                     Read-only admin for usage and audit data
├── tests.py                     Test suite
├── management/commands/
│   └── delete_expired_data.py   Retention cleanup
└── migrations/                  0001 to 0007
templates/emails/                Subject, text and HTML templates for confirmation and reset mails
cron/                            Cron container entrypoint and crontab
tools/                           Synthetic test PDF generator
docs/                            This documentation
```

A good order for reading the code: `urls.py`, then `views.py` for the endpoint you care about, then `services.py` and `tasks.py` for the processing pipeline, and `middleware.py` for what happens before a view runs.

## Working on the documentation

The `docs/` directory is a Jekyll site built by `pages.yml` and published with GitHub Pages. Internal links use the `relative_url` filter, and the navigation is defined by `header_pages` in `docs/_config.yml`. Keep the pages in step with the code, especially the API reference and the configuration tables.

## Related pages

- [Architecture]({{ '/architecture/' | relative_url }})
- [Configuration]({{ '/configuration/' | relative_url }})
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }})
