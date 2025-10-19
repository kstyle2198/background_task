# app/main.py
import asyncio
import json
from fastapi import FastAPI, HTTPException
from celery.result import AsyncResult
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import redis.asyncio as redis
from app.tasks import long_running_task

from .utils.config import get_config
from .utils.setlogger import setup_logger
config = get_config()
logger = setup_logger(f"{__name__}", level=config.LOG_LEVEL)


# 요청 모델 정의
class EmailRequest(BaseModel):
    email_address: str

app = FastAPI()

redis_subscriber_client = redis.from_url(config.REDIS_PUBSUB_URL, decode_responses=True)

@app.post("/send-email/")
async def trigger_email(request: EmailRequest):
    result = long_running_task.delay(request.email_address)
    return {
        "message": f"Email to {request.email_address} has been queued.",
        "task_id": result.id,
        "status": "queued"
    }

@app.get("/stream-results/{task_id}")
async def stream_results(task_id: str):
    
    async def event_generator():
        """
        Redis Pub/Sub 채널을 구독하고 메시지가 오면 yield하는 생성기
        """
        channel_name = f"task_results:{task_id}"
        pubsub = redis_subscriber_client.pubsub()
        await pubsub.subscribe(channel_name)
        
        try:
            while True:
                # 1. Polling(sleep) 대신, 메시지가 올 때까지 비동기로 대기
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, 
                    timeout=60  # 60초간 메시지 없으면 타임아웃
                )
                
                if message is None:
                    # 60초 타임아웃 발생 -> 클라이언트 연결 유지를 위한 'ping'
                    yield {"event": "ping", "data": "Waiting for task..."}
                    continue # 다시 메시지 대기
                
                # 2. 작업자로부터 메시지 도착! +JSON decode
                message_data = message["data"]
                if isinstance(message_data, bytes):
                    message_data = message_data.decode("utf-8")
                data = json.loads(message_data)
                
                # 3. 클라이언트에게 받은 데이터를 그대로 전송
                yield {"event": data["event"], "data": data["data"]}
                
                # 4. 작업이 완료되었으므로(성공/실패 무관) 루프 및 스트림 종료
                break
                
        except asyncio.CancelledError:
            # 클라이언트 연결이 끊어지면 발생
            print(f"Client disconnected from {task_id}")
            raise
        finally:
            # 스트림이 어쨌든 종료되면 구독 해제
            print(f"Unsubscribing from {channel_name}")
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()

    return EventSourceResponse(event_generator())