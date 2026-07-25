---
title: Project Structure
permalink: /project-structure/
---

# Project Structure
{: #project-structure }

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
├── docs/                          # This documentation site (Jekyll + Minima)
├── .github/
│   └── workflows/
│       ├── codacy.yml              # Codacy security scan CI workflow
│       └── pages.yml               # Builds & deploys this docs site to GitHub Pages
├── manage.py                     # Django management CLI
├── .env.example                   # Template for required environment variables
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── LICENSE                        # MIT License
└── requirements.txt
```

## License
{: #license }

This project is licensed under the [MIT License](https://github.com/{{ site.repository | default: "your-username/statement-ai" }}/blob/main/LICENSE).

**⭐ If you like Statement AI, consider giving the repo a star!**
