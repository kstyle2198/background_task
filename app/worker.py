# app/worker.py
from celery import Celery
import os

# Fetch Celery configuration from environment variables
celery_app = Celery(
    'background_tasks',
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

celery_app.conf.update(result_expires=60)  # Results expire after 1 minute
celery_app.autodiscover_tasks(['app.tasks'])
