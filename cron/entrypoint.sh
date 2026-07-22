#!/bin/sh
set -e

# Cron jobs run in a stripped-down environment by default and would not see
# variables passed via `docker compose environment:` (SECRET_KEY, DEBUG,
# DATA_RETENTION_DAYS, ...). Writing them to /etc/environment makes them
# available to the cron job via Debian cron's PAM integration.
printenv | grep -v "no_proxy" > /etc/environment

# Install the cron job directly as a /etc/cron.d file (requires an explicit
# user column, unlike `crontab -e`). Avoids depending on the `crontab`
# binary/PATH.
mkdir -p /etc/cron.d
cp /app/cron/statement-ai-cron /etc/cron.d/statement-ai-cron
chmod 0644 /etc/cron.d/statement-ai-cron

echo "Cron sidecar started. Retention cleanup scheduled: $(tail -n1 /app/cron/statement-ai-cron)"

# Run cron in the foreground so the container stays alive.
cron -f