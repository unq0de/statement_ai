import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'statement_ai.settings')

app = Celery('statement_ai')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()