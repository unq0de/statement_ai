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

EXPOSE 8001

CMD ["sh", "-c", "python manage.py collectstatic --noinput && exec gunicorn statement_ai.wsgi:application --bind 0.0.0.0:8001 --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-60} ${GUNICORN_EXTRA_ARGS:-}"]