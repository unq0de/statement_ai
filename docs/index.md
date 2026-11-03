---
layout: home
title: Statement AI
---

<div align="center">

# Statement AI

A simple and reliable API for processing bank statement PDFs, extracting transactions, and turning them into structured financial data.

<p>
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/django-4.2-092E20?logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/drf-3.14-red?logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/postgres-15-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
</p>

<a href="api-reference/">API Reference</a>
·
<a href="https://github.com/unq0de/statement_ai">GitHub</a>
·
<a href="https://github.com/unq0de/statement_ai#readme">README</a>

</div>

## Overview

Statement AI helps you upload bank statement PDFs, organize the data, and keep everything scoped to the correct user. The API validates the uploaded file, extracts relevant transaction information, and makes the result available in a structured, easy-to-consume format.

It is designed for a clear workflow:

1. Upload a PDF statement
2. Store it securely per user
3. Extract the transaction data
4. Review the saved transactions and evaluation
5. Export or manage the data when needed

## Why this project exists

Many finance workflows still depend on manual extraction from PDF statements. This project gives you a clean backend structure to automate that process without adding unnecessary complexity.

The result is a backend that is:

- secure and user-isolated
- easy to run locally with Docker
- structured around bank statements and transactions
- suitable for personal finance and financial data processing workflows

## Core features

- PDF upload and validation
- Per-user statement storage
- Structured transaction extraction
- Statement analytics and evaluation results
- JWT authentication
- Account deletion and personal data export
- Docker-based local setup

## How it works

The typical flow looks like this:

```text
Upload PDF
  -> validate file type and content
  -> store statement for the authenticated user
  -> extract transactions and metadata
  -> save processed data
  -> return statement and transaction records
```

Everything is scoped to the logged-in user, so data from one account is never exposed to another user.

## Quick start

### Prerequisites

- Docker and Docker Compose
- A Google Gemini API key

### Local setup

```bash
git clone https://github.com/unq0de/statement_ai.git
cd statement_ai
cp .env.example .env
```

Add your environment values, then start the app:

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
```

The API will be available at:

```text
http://localhost:8001/api/
```

## API at a glance

The API exposes a small set of authenticated endpoints for users, statements, transactions, and account management.

- User registration and login
- Statement upload and listing
- Statement detail and file download
- Transaction listing and lookup
- Analytics and summary data
- Account deletion and export

See the [API Reference](api-reference/) for the full documentation.

## Project structure

```text
statement_ai/
├── statement_ai/          # Django project configuration
├── statements/            # API views, models, serializers, services
├── docs/                  # GitHub Pages documentation
├── cron/                  # scheduled cleanup job
├── tools/                 # local helper scripts
├── docker-compose.yml     # local stack setup
├── Dockerfile             # application container
├── requirements.txt       # Python dependencies
├── manage.py              # Django entry point
└── README.MD              # project overview
```

## Built for clarity

This project aims to stay simple and practical:

- clear API boundaries
- explicit ownership checks
- straightforward local setup
- easy-to-follow documentation

It is meant to be useful for real-world development and testing without becoming heavy or over-engineered.

## Open the docs

- [API Reference](api-reference/)
- [GitHub Repository](https://github.com/unq0de/statement_ai)

