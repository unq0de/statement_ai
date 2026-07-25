---
title: Features
permalink: /features/
---

# Features
{: #features }

## Security & Access
{: #security-access }

- JWT-based authentication (access + refresh tokens)
- Per-user data isolation — every user only ever sees their own statements and transactions
- Authenticated, ownership-checked downloads — original PDFs are never publicly reachable

## AI Processing
{: #ai-processing }

- Automatic transaction extraction and categorization via Google Gemini
- AI-generated financial summary per statement

## Data Management
{: #data-management }

- PDF upload with type & size validation
- Full account erasure and configurable data retention (GDPR Art. 17)
- Personal data export as JSON (GDPR Art. 15/20)

## Operations
{: #operations }

- Fully dockerized (Django + PostgreSQL)
- Automated retention cleanup via a cron sidecar

---

Next: see the [Tech Stack]({{ '/tech-stack/' | relative_url }}) behind these features, or jump straight to [Getting Started]({{ '/getting-started/' | relative_url }}).
