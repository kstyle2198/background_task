# backend/main.py
import asyncio
import json
from fastapi import FastAPI, HTTPException
from celery.result import AsyncResult
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from typing import Optional, List, Any

import redis.asyncio as redis
from backend.tasks import long_running_task

from .utils.config import get_config
from .utils.setlogger import setup_logger
config = get_config()
logger = setup_logger(f"{__name__}", level=config.LOG_LEVEL)


# 요청 모델 정의
class EmailRequest(BaseModel):
    email_address: str

app = FastAPI()



# ⭐️ 폴링 엔드포인트 추가
@app.get("/task_status/{task_id}", tags=["General"])
async def get_task_status(task_id: str):
    """
    Celery task_id로 상태와 결과를 조회하는 API
    """
    result = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,     # PENDING / STARTED / RETRY / FAILURE / SUCCESS
        "result": result.result if result.successful() else None
    }



@app.post("/test_for_five_seconds/", tags=["Test"])
async def trigger_email(request: EmailRequest):
    result = long_running_task.delay(request.email_address)
    return {
        "message": f"Email to {request.email_address} has been queued.",
        "task_id": result.id,
        "status": "queued"
    }

