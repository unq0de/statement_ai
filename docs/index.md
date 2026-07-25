---
title: Introduction
permalink: /
nav_order: 1
---

# Statement AI
{: #statement-ai }

**AI-powered REST API that reads bank statement PDFs, categorizes every transaction, and generates financial summaries.**

Statement AI reads uploaded bank statements (PDF), has Google Gemini detect, categorize, and summarize every transaction — and serves it all through a clean, JWT-secured REST API with full per-user data isolation.

| | |
|---|---|
| **Framework** | Django 4.2 + Django REST Framework |
| **AI** | Google Gemini (`gemini-2.5-flash`) |
| **Database** | PostgreSQL 15 |
| **Deployment** | Docker / Docker Compose |
| **License** | [MIT]({{ '/project-structure/' | relative_url }}) |

## Where to start
{: #where-to-start }

This site covers everything beyond the basics. For the fastest path to a running instance, use the **Quickstart** section in the project's [`README`](https://github.com/{{ site.repository | default: "your-username/statement-ai" }}#quickstart) on GitHub — it walks through cloning the repo, configuring `.env`, and starting the Docker stack in five steps.

Once you're up and running, use the sidebar to dig into:

- **[Features]({{ '/features/' | relative_url }})** — what the API does, at a glance.
- **[Tech Stack]({{ '/tech-stack/' | relative_url }})** — the technologies behind it.
- **[Getting Started]({{ '/getting-started/' | relative_url }})** — detailed installation, environment variables, and the scheduled data-retention cleanup.
- **[Using Supabase]({{ '/supabase/' | relative_url }})** — swapping the local Postgres container for a hosted Supabase database.
- **[Privacy & GDPR]({{ '/privacy-gdpr/' | relative_url }})** — the data-protection measures built into the API.
- **[API Reference]({{ '/api-reference/' | relative_url }})** — every endpoint, request/response shape, and error case.
- **[Project Structure]({{ '/project-structure/' | relative_url }})** — how the codebase is organized.

## Disclaimer
{: #disclaimer }

Statement AI processes financial data extracted from real bank statements. Please read the full [Privacy & GDPR]({{ '/privacy-gdpr/' | relative_url }}) page before deploying it for real users — it is **not legal advice**, and you remain responsible for having a valid legal basis and, where applicable, a Data Processing Agreement with Google covering the transfer of statement data to the Gemini API.
