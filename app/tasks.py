# app/tasks.py
from app.worker import celery_app
from .utils import send_email

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process(self, email_address):
    try:
        result = send_email(email_address)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)