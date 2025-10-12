# app/tasks.py
from pydantic import ValidationError, BaseModel
import time
import logging
from .utils.setlogger import setup_logger
logger = setup_logger(f"{__name__}", level=logging.INFO)

from app.worker import celery_app
from .processes.bg_process import send_email

# @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
# def process(self, email_address):
#     try:
#         result = send_email(email_address)
#         logger.info(result)
#         return result
#     except ConnectionError as exc:
#         # 네트워크 에러는 재시도
#         logger.debug("ConnectionError --> Retry")
#         raise self.retry(exc=exc, countdown=30)
#     except ValidationError as exc:
#         # 검증 에러는 재시도 의미 없음
#         logger.error(f"ValidationError : {exc}")
#         return {"error": "Invalid email address"}
#     except Exception as exc:
#         # 예상치 못한 에러는 로깅 후 재시도
#         logger.error(f"Unexpected error: {exc}")
#         raise self.retry(exc=exc)
    

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process(self, email_address, with_progress=False):
    """
    진행률 업데이트를 지원하는 이메일 처리 태스크
    """
    try:
        if with_progress:
            # 진행률 업데이트
            self.update_state(
                state='PROGRESS',
                meta={'current': 0, 'total': 100, 'status': 'Starting...'}
            )
        
        # 1. 이메일 검증 단계
        if with_progress:
            self.update_state(
                state='PROGRESS',
                meta={'current': 25, 'total': 100, 'status': 'Validating email...'}
            )
        
        # 이메일 검증 로직 (간단한 예제)
        if '@' not in email_address:
            raise ValueError("Invalid email format")
        
        # 2. 이메일 준비 단계
        if with_progress:
            self.update_state(
                state='PROGRESS',
                meta={'current': 50, 'total': 100, 'status': 'Preparing email content...'}
            )
        time.sleep(1)  # 시뮬레이션
        
        # 3. 이메일 전송 단계
        if with_progress:
            self.update_state(
                state='PROGRESS',
                meta={'current': 75, 'total': 100, 'status': 'Sending email...'}
            )
        
        result = send_email(email_address)
        
        if with_progress:
            self.update_state(
                state='PROGRESS',
                meta={'current': 100, 'total': 100, 'status': 'Email sent successfully!'}
            )
        
        return {
            "email": email_address,
            "status": "sent",
            "message_id": result.message_id if hasattr(result, 'message_id') else "unknown"
        }
        
    except Exception as exc:
        if with_progress:
            self.update_state(
                state='FAILURE',
                meta={'current': 100, 'total': 100, 'status': f'Error: {str(exc)}'}
            )
        raise self.retry(exc=exc)