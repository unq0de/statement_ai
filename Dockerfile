FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x cron/entrypoint.sh

# Standard-Port für Cloud Run setzen
ENV PORT=8080
EXPOSE 8080

# Production-Start mit Gunicorn
# WICHTIG: Ersetze 'DEIN_PROJEKTNAME' mit dem Namen deines Django-Projektordners (wo die wsgi.py liegt)
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 statement_ai.wsgi:application
