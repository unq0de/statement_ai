---
layout: page
title: Troubleshooting
permalink: /troubleshooting/
---

# Troubleshooting

These are the most common problems you may run into while setting up and using the application.

## Docker Compose fails to start

Check that Docker is running and that the required ports are free.

```bash
docker compose ps
```

If a service crashes, inspect its logs:

```bash
docker compose logs web
docker compose logs db
docker compose logs cron
```

## Missing environment variables

The application raises a runtime error in production when required values such as `SECRET_KEY` or `GEMINI_API_KEY` are missing.

Make sure your `.env` file contains the required values before starting the stack.

## Database connection issues

If the database does not become healthy, verify the values in `.env`:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=statement_ai_db
POSTGRES_USER=statement_ai_user
POSTGRES_PASSWORD=statement_ai_password
```

You can also test the database connectivity from inside the app container:

```bash
docker compose exec web python - <<'PY'
import os
print(os.environ.get('POSTGRES_HOST'))
print(os.environ.get('POSTGRES_DB'))
PY
```

## PDF upload is rejected

The upload endpoint rejects invalid files, including content that is not a valid PDF or files larger than 10 MB.

Common causes:

- the file is not actually a PDF
- the content-type is incorrect
- the file is over the upload limit
- the document was corrupted or truncated

## Gemini processing errors

If the AI step fails, the project logs the exception and returns a `500 Internal Server Error` response. This usually means one of the following:

- the API key is missing or invalid
- the Google SDK is not available
- the PDF is malformed or not usable by Gemini
- the response from Gemini is not valid JSON

Check the logs with:

```bash
docker compose logs web
```

## 401 Unauthorized responses

A `401` usually means the access token is missing, expired, or invalid.

Use the login flow to obtain a new token and then send it in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

## Statement not visible after upload

If the statement was created but not listed, check the user relationship and confirm that the file was processed successfully.

The API only returns statements that belong to the authenticated user.

## Want to clean old data manually

You can trigger retention cleanup directly:

```bash
docker compose exec cron python manage.py delete_expired_data
```

Or run it on the web container if you prefer:

```bash
docker compose exec web python manage.py delete_expired_data
```

## Related pages

- [Installation]({{ '/installation/' | relative_url }})
- [Features]({{ '/features/' | relative_url }})
- [API reference]({{ '/api-reference/' | relative_url }})
