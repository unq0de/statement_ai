---
layout: page
title: Getting Started
permalink: /getting-started/
---

# Getting started

This project is a backend API built with Django and Django REST Framework. It is designed for people who want to upload PDF bank statements, extract the transactions, and keep all data scoped to a single user.

If you are new to the project, the simplest flow is:

1. Clone the repository.
2. Copy the example environment file.
3. Start PostgreSQL and the Django app with Docker Compose.
4. Apply database migrations.
5. Register a user, log in, and upload a PDF.

## Prerequisites

Before you begin, make sure you have:

- Docker and Docker Compose installed
- A Google Gemini API key from Google AI Studio
- Access to a terminal with Git

## Step 1: Clone the repository

```bash
git clone https://github.com/unq0de/statement_ai.git
cd statement_ai
```

This gives you the application code, local configuration files, and the Docker setup.

## Step 2: Create an environment file

```bash
cp .env.example .env
```

Edit `.env` and set the required values. At minimum, add a secure Django secret and your Gemini API key.

## Step 3: Start the application stack

```bash
docker compose up -d --build
```

This starts:

- the Django web application on port `8001`
- a PostgreSQL database on port `5432`
- the custom retention cron job

## Step 4: Run database migrations

```bash
docker compose exec web python manage.py migrate
```

This creates the database schema for the `BankStatement` and `Transaction` models.

## Step 5: Optional admin account

If you want to use the Django admin interface, create a superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

The admin is available at:

```text
http://localhost:8001/admin/
```

## Step 6: Verify that the API is online

Open the API root:

```text
http://localhost:8001/api/
```

The app is ready once the HTTP response comes back and the login endpoints are available.

## Step 7: Register and log in

Create a user:

```bash
curl -X POST http://localhost:8001/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"StrongPass123!"}'
```

Then log in:

```bash
curl -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"StrongPass123!"}'
```

The response contains the `access` and `refresh` tokens you will use for authenticated requests.

## Step 8: Upload your first statement

```bash
curl -X POST http://localhost:8001/api/statements/upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/statement.pdf"
```

The backend validates the file, stores it as a statement tied to the logged-in user, and tries to extract transactions and a summary using Gemini.

## Next steps

- Continue to the [installation guide]({{ '/installation/' | relative_url }}) for environment details.
- Review the [features overview]({{ '/features/' | relative_url }}) to understand the supported workflows.
- Use the [API reference]({{ '/api-reference/' | relative_url }}) for endpoint-by-endpoint documentation.
