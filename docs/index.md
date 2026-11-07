---
layout: home
title: Statement AI
---

<div align="center">

# Statement AI

A backend for processing bank statement PDFs, extracting transactions, categorizing them, and returning structured financial data through a secure REST API.

<p>
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/django-4.2-092E20?logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/drf-3.14-red?logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/postgres-15-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/gemini-ai-8E75B2?logo=googlegemini&logoColor=white" alt="Google Gemini" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
</p>

[Getting started]({{ '/getting-started/' | relative_url }}) ·
[Installation]({{ '/installation/' | relative_url }}) ·
[Features]({{ '/features/' | relative_url }}) ·
[API Reference]({{ '/api-reference/' | relative_url }}) ·
[Security]({{ '/security/' | relative_url }}) ·
[Troubleshooting]({{ '/troubleshooting/' | relative_url }})

</div>

## What this project does

Statement AI is a Django REST API for personal finance workflows. You upload a PDF bank statement, the application validates the file, and then the backend sends the document to Google Gemini for extraction and categorization. The result is saved in a per-user database with structured transactions and an AI-generated summary.

The project is deliberately small and practical. It focuses on a clear flow:

1. Create an account or log in.
2. Upload a PDF bank statement.
3. Validate the file and process it.
4. Review extracted transactions and AI evaluation.
5. Manage, export, or delete your data.

## Main capabilities

- JWT authentication for user sessions
- Upload and validation of PDF statement files
- Transaction extraction and categorization with Google Gemini
- AI-generated evaluation for each processed statement
- Secure ownership checks for statement and transaction access
- Personal data export and account deletion
- Daily automatic cleanup for expired statements
- Local Docker-based setup with PostgreSQL

## Typical workflow

```text
Upload PDF
  -> validate file type and metadata
  -> store statement for the authenticated user
  -> call Gemini to read the document
  -> save extracted transactions and summary
  -> return the statement with its data
```

## Quick start

You can get the application running locally in a few steps:

```bash
git clone https://github.com/unq0de/statement_ai.git
cd statement_ai
cp .env.example .env
```

Then start the stack. The one-off Compose migration service applies the schema before the API, worker, and cron services start:

```bash
docker compose up -d --build
```

The API is exposed at:

```text
http://localhost:8001/api/
```

## Project structure

```text
statement_ai/
├── statement_ai/         # Django project settings and routing
├── statements/           # Models, views, serializers, services
├── docs/                 # GitHub Pages documentation
├── cron/                 # retention cleanup sidecar
├── tools/                # PDF generation helper scripts
├── testdata/             # sample PDFs for testing
├── Dockerfile            # application image
├── docker-compose.yml    # local services
├── manage.py             # Django entry point
├── requirements.txt      # Python requirements
├── README.MD             # project overview
├── .env.example          # environment configuration
└── .env                  # local secrets (not committed)
```

## Where to go next

- [Getting started]({{ '/getting-started/' | relative_url }}) for a guided introduction
- [Installation]({{ '/installation/' | relative_url }}) for environment and Docker setup
- [Features]({{ '/features/' | relative_url }}) for workflow and capability documentation
- [API Reference]({{ '/api-reference/' | relative_url }}) for endpoint details
- [Security]({{ '/security/' | relative_url }}) for privacy and retention information
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }}) for common setup issues

## Repository

- [GitHub repository](https://github.com/unq0de/statement_ai)
- [README](https://github.com/unq0de/statement_ai#readme)

