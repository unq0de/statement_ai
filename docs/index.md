---
title: Statement AI Documentation
---

[Getting Started]({{ site.baseurl }}/getting-started/) ·
[Features & Tech Stack]({{ site.baseurl }}/features/) ·
[Using Supabase]({{ site.baseurl }}/supabase/) ·
[Privacy & GDPR]({{ site.baseurl }}/privacy-gdpr/) ·
[API Reference]({{ site.baseurl }}/api-reference/) ·
[Project Structure]({{ site.baseurl }}/project-structure/)

# Statement AI

**AI-powered REST API that reads bank statement PDFs, categorizes every transaction, and generates financial summaries.**

![Python](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/django-4.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.14-red?logo=django&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-8E75B2?logo=googlegemini&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%2015-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/deploy-Docker-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

> Statement AI reads uploaded bank statements (PDF), has Google Gemini detect, categorize, and summarize every transaction — and serves it all through a clean, JWT-secured REST API with full per-user data isolation.

This site is the full documentation for the project. The [README on GitHub](https://github.com/unq0de/statement_ai) only covers the quickstart and legal disclaimer — everything else lives here:

| Page | Contents |
|---|---|
| [Getting Started]({{ site.baseurl }}/getting-started/) | Prerequisites, installation, environment variables, scheduled retention cleanup |
| [Features & Tech Stack]({{ site.baseurl }}/features/) | What the API does, and what it's built with |
| [Using Supabase]({{ site.baseurl }}/supabase/) | Running against a hosted Supabase Postgres instead of the local container |
| [Privacy & GDPR]({{ site.baseurl }}/privacy-gdpr/) | Data protection measures, retention, Gemini data handling |
| [API Reference]({{ site.baseurl }}/api-reference/) | Every endpoint, request/response bodies, error cases, data models |
| [Project Structure]({{ site.baseurl }}/project-structure/) | Repository layout |

For the fastest path to a running instance, see the **Quickstart** section in the [README](https://github.com/unq0de/statement_ai#quickstart).
