---
title: Features & Tech Stack
---

[Home]({{ site.baseurl }}/) ·
[Getting Started]({{ site.baseurl }}/getting-started/) ·
[Using Supabase]({{ site.baseurl }}/supabase/) ·
[Privacy & GDPR]({{ site.baseurl }}/privacy-gdpr/) ·
[API Reference]({{ site.baseurl }}/api-reference/) ·
[Project Structure]({{ site.baseurl }}/project-structure/)

# Features & Tech Stack

## Features

**🔐 Security & Access**
- JWT-based authentication (access + refresh tokens)
- Per-user data isolation — every user only ever sees their own statements and transactions
- Authenticated, ownership-checked downloads — original PDFs are never publicly reachable

**🤖 AI Processing**
- Automatic transaction extraction and categorization via Google Gemini
- AI-generated financial summary per statement

**📄 Data Management**
- PDF upload with type & size validation
- Full account erasure and configurable data retention (GDPR Art. 17)
- Personal data export as JSON (GDPR Art. 15/20)

**🐳 Operations**
- Fully dockerized (Django + PostgreSQL)
- Automated retention cleanup via cron sidecar

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Django 4.2 + Django REST Framework |
| **Auth** | `djangorestframework-simplejwt` |
| **Database** | PostgreSQL 15 |
| **AI** | Google Gemini (`gemini-2.5-flash`) |
| **Deployment** | Docker / Docker Compose |
