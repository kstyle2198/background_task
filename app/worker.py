# app/worker.py
from celery import Celery
import os

# Fetch Celery configuration from environment variables
celery_app = Celery(
    'background_tasks',
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

celery_app.conf.update(result_expires=60,   # Results expire after 1 minute
                       worker_prefetch_multiplier=1,  # 과도한 프리페칭 방지
                       task_acks_late=True,  # 재시도 시 메시지 손실 방지
                       task_reject_on_worker_lost=True)  # 워커 다운 시 재시도)  
celery_app.autodiscover_tasks(['app.tasks'])
