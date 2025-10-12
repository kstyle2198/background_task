# app/tasks.py
from pydantic import ValidationError, BaseModel
import logging
from .utils.setlogger import setup_logger
logger = setup_logger(f"{__name__}", level=logging.INFO)

from app.worker import celery_app
from .processes.bg_process import send_email

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process(self, email_address):
    try:
        result = send_email(email_address)
        logger.info(result)
        return result
    except ConnectionError as exc:
        # 네트워크 에러는 재시도
        logger.debug("ConnectionError --> Retry")
        raise self.retry(exc=exc, countdown=30)
    except ValidationError as exc:
        # 검증 에러는 재시도 의미 없음
        logger.error(f"ValidationError : {exc}")
        return {"error": "Invalid email address"}
    except Exception as exc:
        # 예상치 못한 에러는 로깅 후 재시도
        logger.error(f"Unexpected error: {exc}")
        raise self.retry(exc=exc)