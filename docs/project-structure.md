---
title: Project Structure
---

# Project Structure

```
statement_ai/
├── statement_ai/                 # Django project
│   ├── settings.py                # Settings, incl. local/Supabase DB switch & global exception handler
│   ├── urls.py                    # Root URL config (includes statements/urls.py under /api/)
│   └── wsgi.py                    # WSGI entrypoint
├── statements/                   # Main app
│   ├── models.py                  # BankStatement & Transaction models
│   ├── serializers.py             # DRF serializers
│   ├── services.py                # Gemini AI integration (extraction, categorization, evaluation)
│   ├── views.py                   # API views
│   ├── urls.py                    # App-level routes
│   ├── exceptions.py              # Project-wide DRF exception handler (consistent JSON errors)
│   ├── management/
│   │   └── commands/
│   │       └── delete_expired_data.py   # GDPR retention cleanup command
│   └── migrations/
│       ├── 0001_initial.py
│       └── 0002_transaction_payee_payer_and_more.py
├── cron/
│   ├── entrypoint.sh              # Cron sidecar entrypoint
│   └── statement-ai-cron          # Crontab: daily retention cleanup schedule
├── .github/
│   └── workflows/
│       └── codacy.yml             # Codacy security scan CI workflow
├── docs/                         # This documentation site (GitHub Pages, Minimal theme)
├── manage.py                     # Django management CLI
├── .env.example                   # Template for required environment variables
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── LICENSE                        # MIT License
└── requirements.txt
```
