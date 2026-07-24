<div align="center">

# Statement AI

### AI-powered REST API that reads bank statement PDFs, categorizes every transaction, and generates financial summaries

<p>
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/django-4.2-092E20?logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/DRF-3.14-red?logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/AI-Google%20Gemini-8E75B2?logo=googlegemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/database-PostgreSQL%2015-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/deploy-Docker-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

<p>
  <b>🔐 JWT Auth</b> &nbsp;•&nbsp;
  <b>📄 PDF Upload</b> &nbsp;•&nbsp;
  <b>🤖 AI Categorization</b> &nbsp;•&nbsp;
  <b>📊 Auto-Summary</b> &nbsp;•&nbsp;
  <b>🗑️ GDPR-ready</b>
</p>

<p>
  <a href="#quickstart">Quickstart</a> ·
  <a href="https://unq0de.github.io/statement_ai/"><b>📖 Full Documentation</b></a> ·
  <a href="#disclaimer">Disclaimer</a>
</p>

</div>

<br>

> Statement AI reads uploaded bank statements (PDF), has Google Gemini detect, categorize, and summarize every transaction — and serves it all through a clean, JWT-secured REST API with full per-user data isolation.

---

## Quickstart

Requires **Docker & Docker Compose** and a [Google Gemini API key](https://aistudio.google.com/apikey).

**1. Clone the repo**

```bash
git clone https://github.com/<your-username>/statement-ai.git
cd statement-ai
```

**2. Create your environment file**

```bash
cp .env.example .env
```

Fill in `SECRET_KEY` and `GEMINI_API_KEY` at minimum.

**3. Start the stack**

```bash
docker compose up -d --build
```

This starts the `web`, `cron`, and local Postgres services.

**4. Run migrations**

```bash
docker compose exec web python manage.py migrate
```

**5. Create an admin user** *(optional, for `/admin`)*

```bash
docker compose exec web python manage.py createsuperuser
```

The API is now running at `http://localhost:8000/api/`.

📖 For the full guide — environment variables, using Supabase instead of local Postgres, retention cleanup, all API endpoints, data models, and the project structure — see the **[full documentation](https://unq0de.github.io/statement_ai/)**.

---

## Disclaimer

Statement AI processes financial data extracted from bank statements, which is personal data under the GDPR. Technical measures such as JWT-secured access, per-user data isolation, configurable data retention, and personal data export/erasure endpoints are implemented — see the [Privacy & GDPR page](https://unq0de.github.io/statement_ai/privacy-gdpr/) in the full documentation for details.

> ⚖️ This project's privacy and GDPR-related features describe the **technical measures available in the API** — **not legal advice**. Consult a data protection professional before processing real users' financial data in production. If you operate this API for real users in the EU/EEA, you are responsible for having a valid legal basis and a Data Processing Agreement (DPA) with Google covering the transfer of statement data to Gemini (Google LLC, USA).

---

<div align="center">

## License

This project is licensed under the [MIT License](LICENSE).

<br>

**⭐ If you like Statement AI, consider giving the repo a star!**

</div>
