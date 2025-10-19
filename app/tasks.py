# app/tasks.py
import json
import redis  # 동기 redis 클라이언트 (Celery 작업자용)
from .utils.setlogger import setup_logger
from .utils.config import get_config
config = get_config()
logger = setup_logger(f"{__name__}", level=config.LOG_LEVEL)

from app.worker import celery_app
from .processes.bg_process import send_email
from pydantic import ValidationError

# Celery 작업자가 결과를 발행할 때 사용할 동기 Redis 클라이언트
# Pub/Sub용으로 DB 2번을 사용 (분리)
redis_pubsub_client = redis.Redis.from_url(config.REDIS_PUBSUB_URL)

# bind=True: 태스크 함수 안에서 self (태스크 인스턴스)에 접근 가능
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def long_running_task(self, email_address: str):
    """
    작업 완료 후 Pub/Sub으로 결과를 발행하는 태스크
    """
    task_id = self.request.id
    channel_name = f"task_results:{task_id}"
    
    try:
        logger.info(f"Task {task_id} started...")
        result = send_email(email_address)
        logger.info(f"Task {task_id} finished.")
        
        # 성공 결과를 JSON으로 만들어 채널에 발행
        payload = json.dumps({"event": "task_result", "data": result})
        redis_pubsub_client.publish(channel_name, payload)
        
        return result  # Celery 백엔드에도 결과 저장
    
    except ConnectionError as exc:
        # 네트워크 에러는 재시도
        logger.debug("ConnectionError --> Retry")
        raise self.retry(exc=exc, countdown=30)
    except ValidationError as exc:
        # 검증 에러는 재시도 의미 없음
        logger.error(f"ValidationError : {exc}")
        return {"error": "Invalid email address"}
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        # 실패 결과를 JSON으로 만들어 채널에 발행
        payload = json.dumps({"event": "task_error", "data": str(e)})
        redis_pubsub_client.publish(channel_name, payload)
        # Celery가 이 태스크를 '실패'로 기록하도록 예외를 다시 발생시킴
        raise
